"""
Extract gaming-specific catalyst signals from SEC filings.
"""

import argparse
import json
import os
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from dotenv import load_dotenv

load_dotenv()

RAW_METADATA_DIR = Path("data/raw/gaming/sec")
RAW_TEXT_DIR = RAW_METADATA_DIR / "filings_text"
OUT_DIR = Path("data/processed/gaming_sec_catalysts")
DEFAULT_TRACKED_FILE = Path("data/raw/gaming/studio_candidates.json")
USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "GamingTracker research@example.com")
EDGAR_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"

CATALYST_PATTERNS = {
    "release_delay": [
        r"(?:delay(?:ed|s|ing)?|postpone(?:d|s|ment)?|push(?:ed)?\s+back).{0,80}?(?:release|launch)",
        r"(?:release|launch)\s+(?:has been|was)?\s*(?:delayed|postponed|moved)",
    ],
    "launch_window": [
        r"(?:launch|release)\s+(?:window|date|timing|schedule)\s*(?:is|was|remains|expected|planned|targeted|scheduled|set)?\s*(?:for|in|on)?\s*(\b(?:Q[1-4]\s+\d{4}|\w+\s+\d{4}|\w+\s+\d{1,2},\s+\d{4})\b)",
        r"(?:expected|planned|targeted|scheduled)\s+to\s+(?:launch|release|ship).{0,30}?(\b(?:Q[1-4]\s+\d{4}|\w+\s+\d{4}|\w+\s+\d{1,2},\s+\d{4})\b)",
    ],
    "publisher_milestone": [
        r"milestone\s+payment",
        r"publisher\s+payment",
        r"development\s+milestone",
        r"(?:alpha|beta|gold).{0,40}?milestone",
    ],
    "certification_signal": [
        r"(?:platform|console).{0,40}?certification",
        r"submitted.{0,40}?(?:sony|xbox|nintendo).{0,40}?(?:certification|approval|lotcheck)",
        r"gold\s+master",
    ],
    "layoff_or_restructure": [
        r"restructuring",
        r"reduction\s+in\s+force",
        r"layoffs?",
        r"headcount\s+reduction",
    ],
    "financing_signal": [
        r"registered\s+direct\s+offering",
        r"at-the-market",
        r"\bATM\b",
        r"private\s+placement",
        r"shelf\s+registration",
    ],
    "impairment_or_writeoff": [
        r"impairment\s+charge",
        r"write-?down",
        r"write-?off",
    ],
}

GENERIC_RISK_PHRASES = [
    "could negatively impact",
    "may negatively impact",
    "risk factors",
    "table of contents",
    "we may",
    "uncertainties",
    "forward-looking statements",
]

TABULAR_RESTRUCTURING_PHRASES = [
    "research and development",
    "marketing and sales",
    "general and administrative",
    "operating expenses",
    "stock-based compensation",
]

SPECIFIC_TIMING_PATTERN = re.compile(
    r"\b(?:Q[1-4]\s+\d{4}|FY\s*\d{4}|\w+\s+\d{4}|\w+\s+\d{1,2},\s+\d{4})\b",
    re.IGNORECASE,
)

ACTIONABLE_RELEASE_PHRASES = [
    "announced",
    "expects",
    "expected",
    "planned",
    "targeted",
    "scheduled",
    "slated",
    "moved to",
    "shifted to",
]


def normalize_cik(cik: str) -> tuple[str, str]:
    """Return unpadded and padded CIK representations."""
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    if not digits:
        raise ValueError("CIK must contain at least one digit")

    cik_unpadded = digits.lstrip("0") or "0"
    cik_padded = cik_unpadded.zfill(10)
    return cik_unpadded, cik_padded


def get_company_filings(cik: str, filing_types: list[str] | None = None) -> list[dict]:
    """Fetch recent SEC submissions metadata for a tracked studio."""
    RAW_METADATA_DIR.mkdir(parents=True, exist_ok=True)

    cik_unpadded, cik_padded = normalize_cik(cik)
    url = f"{EDGAR_SUBMISSIONS_BASE}/CIK{cik_padded}.json"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    response = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
    response.raise_for_status()
    data = response.json()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_METADATA_DIR / f"filings_{cik_padded}_{timestamp}.json"
    raw_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    filings: list[dict] = []
    for index, form_type in enumerate(forms):
        if filing_types and form_type not in filing_types:
            continue

        accession = accessions[index].replace("-", "") if index < len(accessions) else ""
        primary_document = primary_docs[index] if index < len(primary_docs) else ""
        if not accession or not primary_document:
            continue

        filings.append(
            {
                "cik": cik_padded,
                "company_name": data.get("name", ""),
                "ticker": ",".join(data.get("tickers", [])),
                "form_type": form_type,
                "filing_date": dates[index] if index < len(dates) else "",
                "accession_number": accessions[index] if index < len(accessions) else "",
                "primary_document": primary_document,
                "filing_url": f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession}/{primary_document}",
                "source_type": "SEC",
                "source_confidence": "secondary",
            }
        )

    return filings


def load_tracked_studios(path: Path) -> list[dict]:
    """Load tracked gaming studios from a local seed file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("Tracked studios file must contain a JSON array or object")
    return [item for item in payload if isinstance(item, dict)]


def _load_text(file_path: Path | None, filing_url: str | None) -> str:
    if file_path is not None:
        return file_path.read_text(encoding="utf-8")

    if not filing_url:
        raise ValueError("Provide either --file or --url")

    headers = {"User-Agent": USER_AGENT}
    response = httpx.get(filing_url, headers=headers, timeout=60, follow_redirects=True)
    response.raise_for_status()
    RAW_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    out_name = filing_url.rstrip("/").split("/")[-1] or "filing.txt"
    (RAW_TEXT_DIR / out_name).write_text(response.text, encoding="utf-8")
    return response.text


def _clean_text(raw_text: str) -> str:
    parser = "xml" if raw_text.lstrip().startswith("<?xml") else "lxml"
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(raw_text, parser)
    return soup.get_text(separator=" ", strip=True)


def _has_specific_timing(text: str) -> bool:
    return bool(SPECIFIC_TIMING_PATTERN.search(text))


def _is_generic_risk_context(context: str) -> bool:
    lowered = context.lower()
    return any(phrase in lowered for phrase in GENERIC_RISK_PHRASES)


def _is_tabular_restructuring_context(context: str) -> bool:
    lowered = context.lower()
    return any(phrase in lowered for phrase in TABULAR_RESTRUCTURING_PHRASES)


def _should_keep_record(
    metadata: dict,
    catalyst_type: str,
    context: str,
    matched_titles: list[str],
) -> bool:
    form_type = str(metadata.get("form_type", "")).upper()
    has_title = bool(matched_titles)
    has_timing = _has_specific_timing(context)
    lowered = context.lower()

    if catalyst_type == "launch_window" and "press release dated" in lowered:
        return False

    if catalyst_type == "layoff_or_restructure" and _is_tabular_restructuring_context(context):
        return False

    if form_type in {"10-Q", "10-K", "20-F"}:
        if catalyst_type == "release_delay":
            if has_title or has_timing:
                return True
            if any(phrase in lowered for phrase in ACTIONABLE_RELEASE_PHRASES) and not _is_generic_risk_context(context):
                return True
            return False

        if catalyst_type == "launch_window":
            return has_timing and not _is_generic_risk_context(context)

        if catalyst_type == "publisher_milestone":
            return has_title or "payment" in lowered or "royalt" in lowered or "advance" in lowered

        if catalyst_type == "layoff_or_restructure":
            return ("charge" in lowered or "plan" in lowered or "reduction" in lowered or "workforce" in lowered)

    return True


def _dedupe_records(records: list[dict]) -> list[dict]:
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[dict] = []

    for record in records:
        key = (
            str(record.get("filing_url", "")),
            str(record.get("catalyst_type", "")),
            str(record.get("matched_text", "")).strip().lower(),
            str(record.get("title", "")).strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)

    return deduped


def extract_catalysts(text: str, metadata: dict) -> list[dict]:
    clean_text = _clean_text(text)
    results: list[dict] = []
    tracked_title_names = [name for name in metadata.get("tracked_title_names", []) if isinstance(name, str) and name]

    for catalyst_type, patterns in CATALYST_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, clean_text, re.IGNORECASE):
                start = max(0, match.start() - 180)
                end = min(len(clean_text), match.end() + 180)
                now = datetime.now(timezone.utc)
                record = {
                    "catalyst_type": catalyst_type,
                    "matched_text": match.group(0),
                    "context": clean_text[start:end].strip(),
                    "filing_url": metadata.get("filing_url", ""),
                    "filing_date": metadata.get("filing_date", ""),
                    "company_name": metadata.get("company_name", ""),
                    "ticker": metadata.get("ticker", ""),
                    "form_type": metadata.get("form_type", ""),
                    "source_type": "SEC",
                    "source_confidence": "secondary",
                    "extracted_at": now.isoformat(),
                }
                if catalyst_type == "launch_window" and match.groups():
                    record["sponsor_disclosed_target_date"] = match.group(1)
                matched_titles = [title for title in tracked_title_names if title.lower() in record["context"].lower()]
                if matched_titles:
                    record["matched_titles"] = matched_titles
                    if len(matched_titles) == 1:
                        record["title"] = matched_titles[0]
                if _should_keep_record(metadata, catalyst_type, record["context"], matched_titles):
                    results.append(record)

    return _dedupe_records(results)


def save_results(records: list[dict], ticker: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_ticker = re.sub(r"[^A-Za-z0-9._-]+", "_", ticker or "unknown")
    path = OUT_DIR / f"gaming_catalysts_{safe_ticker}_{timestamp}.json"
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return path


def extract_from_tracked_studios(
    tracked_file: Path,
    filing_types: list[str],
    limit_per_company: int,
) -> list[dict]:
    """Fetch and extract gaming catalysts for tracked studios with SEC CIKs."""
    studios = load_tracked_studios(tracked_file)
    all_records: list[dict] = []

    for studio in studios:
        sec_cik = studio.get("sec_cik") or studio.get("cik")
        if not sec_cik:
            continue

        filings = get_company_filings(str(sec_cik), filing_types=filing_types)[:limit_per_company]
        title_names = [title.get("game_title", "") for title in studio.get("titles", []) if isinstance(title, dict)]

        for filing in filings:
            metadata = {
                **filing,
                "company_name": studio.get("company_name", filing.get("company_name", "")),
                "ticker": studio.get("ticker", filing.get("ticker", "")),
                "tracked_title_names": title_names,
            }
            try:
                text = _load_text(None, filing.get("filing_url"))
            except httpx.HTTPError as exc:
                print(f"Skipping {filing.get('filing_url', '')}: {exc}")
                continue
            extracted = extract_catalysts(text, metadata)
            if extracted:
                save_results(extracted, studio.get("ticker", filing.get("ticker", "")))
                all_records.extend(extracted)

    if all_records:
        batch_name = f"gaming_catalysts_batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        batch_path = OUT_DIR / batch_name
        batch_path.write_text(json.dumps(all_records, indent=2), encoding="utf-8")
        print(f"Saved combined batch output to {batch_path}")

    return all_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract gaming catalysts from SEC filing text")
    parser.add_argument("--file", type=Path, help="Local filing text or HTML file")
    parser.add_argument("--url", type=str, help="Remote filing URL")
    parser.add_argument("--batch", action="store_true", help="Fetch filings for all studios in the tracked file")
    parser.add_argument("--tracked-file", type=Path, default=DEFAULT_TRACKED_FILE, help="Tracked studios JSON file")
    parser.add_argument(
        "--types",
        nargs="+",
        default=["8-K", "10-Q", "10-K"],
        help="Filing types to include in batch mode",
    )
    parser.add_argument("--limit-per-company", type=int, default=4, help="Maximum filings to inspect per studio")
    parser.add_argument("--ticker", type=str, default="")
    parser.add_argument("--company-name", type=str, default="")
    parser.add_argument("--filing-date", type=str, default="")
    parser.add_argument("--form-type", type=str, default="")
    args = parser.parse_args()

    if args.batch:
        records = extract_from_tracked_studios(args.tracked_file, args.types, args.limit_per_company)
        print(f"Extracted {len(records)} gaming catalysts from tracked studios")
        return

    raw_text = _load_text(args.file, args.url)
    metadata = {
        "filing_url": args.url or "",
        "filing_date": args.filing_date,
        "company_name": args.company_name,
        "ticker": args.ticker,
        "form_type": args.form_type,
    }
    records = extract_catalysts(raw_text, metadata)
    out_path = save_results(records, args.ticker)
    print(f"Extracted {len(records)} gaming catalysts to {out_path}")


if __name__ == "__main__":
    main()
