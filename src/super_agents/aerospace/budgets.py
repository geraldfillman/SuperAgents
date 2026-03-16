"""DoD budget-document ingestion helpers."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .io_utils import write_json
from .paths import ensure_directory, project_path, slugify

BUDGET_TIMEOUT_SECONDS = float(os.getenv("BUDGET_TIMEOUT_SECONDS", "60"))
BUDGET_USER_AGENT = os.getenv(
    "BUDGET_USER_AGENT",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
)

BUDGET_PDF_DIR = project_path("data", "raw", "budgets", "pdf")
BUDGET_TEXT_DIR = project_path("data", "raw", "budgets", "text")
BUDGET_LINES_DIR = project_path("data", "processed", "budget_lines")

FISCAL_YEAR_RE = re.compile(r"\bFY\s*(20\d{2})\b", re.IGNORECASE)
RDTE_PE_RE = re.compile(r"^PE\s+(?P<program_element>\d{7}[A-Z]?):\s+(?P<title>.+)$")
NUMBER_TOKEN_RE = re.compile(r"-?[\d,]+(?:\.\d+)?")
APPROPRIATION_PREFIXES = (
    "Aircraft Procurement",
    "Defense Production Act Purchases",
    "Missile Procurement",
    "National Guard and Reserve Equipment",
    "Operation and Maintenance",
    "Other Procurement",
    "Procurement",
    "Research, Development, Test & Evaluation",
    "RDT&E",
    "Shipbuilding and Conversion",
    "Weapons Procurement",
)


def _make_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": BUDGET_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://comptroller.defense.gov/Budget-Materials/",
        },
        timeout=BUDGET_TIMEOUT_SECONDS,
        follow_redirects=True,
    )


def normalize_line(value: str) -> str:
    """Collapse PDF text into stable single-line records."""
    return " ".join(value.replace("\x00", " ").split()).strip()


def download_budget_pdf(url: str, *, label: str | None = None, client: httpx.Client | None = None) -> Path:
    """Download an official budget PDF into the raw cache."""
    own_client = client is None
    if own_client:
        client = _make_client()

    try:
        assert client is not None
        response = client.get(url)
        response.raise_for_status()
    finally:
        if own_client:
            client.close()

    parsed = urlparse(url)
    stem = Path(parsed.path).stem or slugify(label or "budget")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = ensure_directory(BUDGET_PDF_DIR) / f"{slugify(label or stem)}_{timestamp}.pdf"
    out_path.write_bytes(response.content)
    return out_path


def extract_pdf_lines(pdf_path: Path) -> list[str]:
    """Extract normalized lines from a PDF using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for raw_line in text.splitlines():
            line = normalize_line(raw_line)
            if line:
                lines.append(line)
    return lines


def save_extracted_text(lines: list[str], *, pdf_path: Path, label: str | None = None) -> Path:
    """Persist extracted PDF text for debugging parser behavior."""
    out_path = ensure_directory(BUDGET_TEXT_DIR) / f"{slugify(label or pdf_path.stem)}.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def infer_document_kind(lines: list[str]) -> str:
    """Infer the supported budget-document family from extracted text."""
    joined = "\n".join(lines[:200]).lower()
    if "exhibit p-1" in joined or "procurement program" in joined:
        return "p1"
    if "exhibit r-2" in joined or "r-1 program element" in joined or "\npe " in f"\n{joined}":
        return "rdte"
    raise ValueError("Could not infer budget document type. Provide --kind explicitly.")


def infer_fiscal_year(lines: list[str], *, source_hint: str = "") -> int:
    """Infer the fiscal year from the source URL, file name, or extracted text."""
    for candidate in (source_hint, " ".join(lines[:200])):
        match = FISCAL_YEAR_RE.search(candidate)
        if match:
            return int(match.group(1))

    filename_match = re.search(r"(20\d{2})", source_hint)
    if filename_match:
        return int(filename_match.group(1))
    raise ValueError("Could not infer fiscal year. Provide --fiscal-year explicitly.")


def infer_agency(lines: list[str], *, kind: str) -> str:
    """Infer the agency label from known document-family cues."""
    joined = "\n".join(lines[:400]).upper()
    if "DARPA" in joined:
        return "Defense Advanced Research Projects Agency"
    if "OFFICE OF THE SECRETARY OF DEFENSE" in joined or "OSD" in joined:
        return "Office of the Secretary Of Defense"
    if kind in {"p1", "rdte"} and "DEFENSE-WIDE" in joined:
        return "Department of Defense"
    raise ValueError("Could not infer agency. Provide --agency explicitly.")


def _split_numeric_suffix(line: str) -> tuple[str, list[str]]:
    tokens = line.split()
    suffix: list[str] = []
    while tokens:
        token = tokens[-1]
        if token in {"-", "--"} or NUMBER_TOKEN_RE.fullmatch(token):
            suffix.insert(0, tokens.pop())
            continue
        break
    return " ".join(tokens), suffix


def _parse_amount(token: str, *, scale: int) -> float:
    if token in {"-", "--"}:
        return 0.0
    cleaned = token.replace(",", "")
    if not cleaned:
        return 0.0
    return round(float(cleaned) * scale, 2)


def _select_p1_amount(tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    return _parse_amount(tokens[-1], scale=1_000)


def _select_rdte_amount(tokens: list[str]) -> float:
    if len(tokens) >= 6:
        return _parse_amount(tokens[5], scale=1_000_000)
    if len(tokens) >= 4:
        return _parse_amount(tokens[-1], scale=1_000_000)
    return 0.0


def _looks_like_appropriation(line: str) -> bool:
    if line.startswith("FY"):
        return False
    return any(line.startswith(prefix) for prefix in APPROPRIATION_PREFIXES)


def _clean_text_label(value: str) -> str:
    cleaned = normalize_line(value)
    cleaned = re.sub(r"\bUNCLASSIFIED\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -")


def _normalize_p1_appropriation(line: str) -> str:
    prefix_text, _ = _split_numeric_suffix(line)
    candidate = prefix_text or line
    candidate = _clean_text_label(candidate)
    candidate = re.sub(r"^Appropriation:\s*", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"^\d{4}[A-Z]?\s+", "", candidate)
    return candidate


def _extract_p1_line_item(prefix_text: str) -> str:
    tokens = prefix_text.split()
    if not tokens or not tokens[0].isdigit():
        return ""

    tokens = tokens[1:]
    while tokens and len(tokens[-1]) <= 2 and tokens[-1].isupper():
        tokens.pop()
    return _clean_text_label(" ".join(tokens))


def parse_p1_budget_lines(
    lines: list[str],
    *,
    agency: str,
    fiscal_year: int,
    status: str,
    source_url: str,
) -> list[dict]:
    """Parse P-1 procurement rows into normalized budget_lines records."""
    appropriation = ""
    records: list[dict] = []

    for line in lines:
        if _looks_like_appropriation(line):
            appropriation = _normalize_p1_appropriation(line)
            continue

        prefix_text, numeric_tokens = _split_numeric_suffix(line)
        if len(numeric_tokens) < 5:
            continue
        if not prefix_text or not prefix_text.split()[0].isdigit():
            continue

        line_item = _extract_p1_line_item(prefix_text)
        if not line_item:
            continue

        records.append(
            {
                "agency": agency,
                "fiscal_year": fiscal_year,
                "appropriation": appropriation,
                "program_element": "",
                "line_item": line_item,
                "amount_usd": _select_p1_amount(numeric_tokens),
                "status": status,
                "source_url": source_url,
                "source_type": "DoD Comptroller PDF",
                "source_confidence": "primary",
            }
        )

    return records


def parse_rdte_budget_lines(
    lines: list[str],
    *,
    agency: str,
    fiscal_year: int,
    status: str,
    source_url: str,
) -> list[dict]:
    """Parse RDT&E program-element rows into normalized budget_lines records."""
    records: list[dict] = []
    current_appropriation = ""
    current_program_element = ""
    current_title = ""
    expect_appropriation = False

    for line in lines:
        if line == "Appropriation/Budget Activity":
            expect_appropriation = True
            current_appropriation = ""
            continue

        if expect_appropriation:
            if line.startswith("R-1 Program Element"):
                expect_appropriation = False
                continue
            if line.startswith("PE "):
                expect_appropriation = False
            else:
                current_appropriation = _clean_text_label(f"{current_appropriation} {line}")
                continue

        match = RDTE_PE_RE.match(line)
        if match:
            current_program_element = match.group("program_element")
            current_title = _clean_text_label(match.group("title"))
            continue

        if line.startswith("Total Program Element") and current_program_element:
            _, numeric_tokens = _split_numeric_suffix(line)
            if not numeric_tokens:
                continue

            records.append(
                {
                    "agency": agency,
                    "fiscal_year": fiscal_year,
                    "appropriation": current_appropriation,
                    "program_element": current_program_element,
                    "line_item": current_title,
                    "amount_usd": _select_rdte_amount(numeric_tokens),
                    "status": status,
                    "source_url": source_url,
                    "source_type": "DoD Comptroller PDF",
                    "source_confidence": "primary",
                }
            )

    return records


def parse_budget_pdf(
    pdf_path: Path,
    *,
    kind: str | None = None,
    agency: str | None = None,
    fiscal_year: int | None = None,
    status: str = "requested",
    source_url: str = "",
    label: str | None = None,
) -> tuple[str, list[dict], Path]:
    """Extract text and parse a supported budget PDF."""
    lines = extract_pdf_lines(pdf_path)
    text_path = save_extracted_text(lines, pdf_path=pdf_path, label=label)

    resolved_kind = kind or infer_document_kind(lines)
    resolved_agency = agency or infer_agency(lines, kind=resolved_kind)
    resolved_fiscal_year = fiscal_year or infer_fiscal_year(lines, source_hint=source_url or pdf_path.name)
    resolved_source_url = source_url or str(pdf_path)

    if resolved_kind == "p1":
        records = parse_p1_budget_lines(
            lines,
            agency=resolved_agency,
            fiscal_year=resolved_fiscal_year,
            status=status,
            source_url=resolved_source_url,
        )
    elif resolved_kind == "rdte":
        records = parse_rdte_budget_lines(
            lines,
            agency=resolved_agency,
            fiscal_year=resolved_fiscal_year,
            status=status,
            source_url=resolved_source_url,
        )
    else:
        raise ValueError(f"Unsupported budget document type: {resolved_kind}")

    return resolved_kind, records, text_path


def save_budget_lines(records: list[dict], *, label: str | None = None) -> Path:
    """Persist normalized budget-line records into the processed cache."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = ensure_directory(BUDGET_LINES_DIR) / f"budget_lines_{slugify(label or 'budget')}_{timestamp}.json"
    write_json(out_path, records)
    return out_path
