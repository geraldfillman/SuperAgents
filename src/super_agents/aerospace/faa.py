"""FAA commercial space page monitor for licensing and stakeholder signals."""

from __future__ import annotations

import os
import re
from dataclasses import asdict
from datetime import datetime

import httpx

from .io_utils import write_json
from .paths import ensure_directory, project_path, slugify
from .watchlist import CompanyRecord, SystemRecord

FAA_TIMEOUT_SECONDS = float(os.getenv("FAA_TIMEOUT_SECONDS", "30"))
FAA_USER_AGENT = os.getenv(
    "FAA_USER_AGENT",
    os.getenv(
        "SEC_EDGAR_USER_AGENT",
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 Safari/537.36"
        ),
    ),
)

FAA_PAGE_CATALOG = (
    "https://www.faa.gov/space/licenses",
    "https://www.faa.gov/space/streamlined_licensing_process",
    "https://www.faa.gov/space/licenses/safety_approvals",
    "https://www.faa.gov/space/stakeholder_engagement",
    "https://www.faa.gov/space/stakeholder_engagement/spacex_starship",
    "https://www.faa.gov/space/stakeholder_engagement/SpaceX_Falcon_Program",
    "https://www.faa.gov/space/stakeholder_engagement/shuttle_landing_facility",
    "https://www.faa.gov/space/stakeholder_engagement/Sierra_at_SLF_VSFB",
    "https://www.faa.gov/space/stakeholder_engagement/spacex_starship_ksc",
)

RAW_FAA_QUERY_DIR = project_path("data", "raw", "faa", "queries")
RAW_FAA_PAGE_DIR = project_path("data", "raw", "faa", "pages")
PROCESSED_FAA_DIR = project_path("data", "processed", "faa_signals")

GENERIC_TERMS = {
    "aircraft",
    "launch",
    "lander",
    "mission",
    "operations",
    "platform",
    "program",
    "services",
    "site",
    "space",
    "support",
    "system",
    "systems",
    "vehicle",
}


def _make_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": FAA_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
        timeout=FAA_TIMEOUT_SECONDS,
        follow_redirects=True,
    )


def _normalize_text(value: str) -> str:
    lowered = "".join(char.lower() if char.isalnum() or char.isspace() else " " for char in value)
    return " ".join(lowered.split())


def _useful_phrase(value: str) -> bool:
    tokens = _normalize_text(value).split()
    if not tokens:
        return False
    return any(len(token) > 2 and token not in GENERIC_TERMS for token in tokens)


def _unique_keywords(values: list[str]) -> list[str]:
    seen: set[str] = set()
    keywords: list[str] = []
    for value in values:
        phrase = value.strip()
        normalized = _normalize_text(phrase)
        if not phrase or not _useful_phrase(phrase) or normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(phrase)
    return keywords


def build_faa_query_manifest(
    company: CompanyRecord,
    *,
    systems: list[SystemRecord] | None = None,
    urls: tuple[str, ...] = FAA_PAGE_CATALOG,
) -> dict:
    """Build a page-monitor manifest for FAA commercial space signals."""
    system_rows = systems or []
    keywords = _unique_keywords(
        [company.company_name]
        + [system.system_name for system in system_rows if system.system_name]
    )
    return {
        "company": asdict(company),
        "systems": [system.to_dict() for system in system_rows],
        "keywords": keywords,
        "source_urls": list(urls),
        "generated_at": datetime.now().isoformat(),
    }


def save_faa_query_manifest(manifest: dict, *, label: str | None = None) -> Path:
    """Persist an FAA query manifest."""
    destination = ensure_directory(RAW_FAA_QUERY_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_label = label or manifest.get("company", {}).get("ticker") or manifest.get("company", {}).get("company_name") or "query"
    out_path = destination / f"faa_query_{slugify(manifest_label)}_{timestamp}.json"
    write_json(out_path, manifest)
    return out_path


def _extract_page_text(html_text: str) -> str:
    without_scripts = re.sub(r"<script\b[^>]*>.*?</script>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
    without_styles = re.sub(r"<style\b[^>]*>.*?</style>", " ", without_scripts, flags=re.IGNORECASE | re.DOTALL)
    without_tags = re.sub(r"<[^>]+>", " ", without_styles)
    collapsed = re.sub(r"\s+", " ", without_tags)
    return collapsed.strip()


def _extract_title(html_text: str) -> str:
    title_match = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if title_match:
        return re.sub(r"\s+", " ", title_match.group(1)).strip()
    heading_match = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if heading_match:
        return re.sub(r"<[^>]+>", " ", heading_match.group(1)).strip()
    return ""


def _extract_last_updated(text: str) -> str:
    match = re.search(
        r"(?:page\s+)?last\s+updated:?\s+((?:[A-Za-z]+,\s+)?[A-Za-z]+\s+\d{1,2},\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else ""


def fetch_faa_pages(urls: tuple[str, ...] = FAA_PAGE_CATALOG, *, client: httpx.Client | None = None) -> list[dict]:
    """Fetch a fixed set of official FAA pages."""
    own_client = client is None
    if own_client:
        client = _make_client()

    records: list[dict] = []
    try:
        assert client is not None
        for url in urls:
            response = client.get(url)
            response.raise_for_status()
            html_text = response.text
            text = _extract_page_text(html_text)
            records.append(
                {
                    "url": url,
                    "title": _extract_title(html_text),
                    "text": text,
                    "last_updated": _extract_last_updated(text),
                    "fetched_at": datetime.now().isoformat(),
                }
            )
    finally:
        if own_client:
            client.close()

    return records


def save_faa_pages(records: list[dict], *, label: str = "catalog") -> Path:
    """Persist fetched FAA page text snapshots."""
    destination = ensure_directory(RAW_FAA_PAGE_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = destination / f"faa_pages_{slugify(label)}_{timestamp}.json"
    write_json(out_path, records)
    return out_path


def _extract_snippet(text: str, keyword: str, radius: int = 180) -> str:
    target = keyword.strip()
    if not target:
        return ""
    if " " in _normalize_text(target):
        match = re.search(re.escape(target), text, flags=re.IGNORECASE)
    else:
        match = re.search(rf"\b{re.escape(target)}\b", text, flags=re.IGNORECASE)
    if match is None:
        return ""
    start = max(match.start() - radius, 0)
    end = min(match.end() + radius, len(text))
    return text[start:end].strip()


def _row_matches(text: str, keyword: str) -> bool:
    normalized_text = _normalize_text(text)
    normalized_keyword = _normalize_text(keyword)
    if not normalized_keyword:
        return False
    if " " in normalized_keyword:
        return normalized_keyword in normalized_text
    keyword_tokens = normalized_keyword.split()
    if not keyword_tokens:
        return False
    text_tokens = set(normalized_text.split())
    return keyword_tokens[0] in text_tokens


def _infer_signal_type(url: str, title: str, text: str) -> tuple[str, str]:
    combined = _normalize_text(f"{title} {text}")
    if "stakeholder engagement" in combined or "/stakeholder_engagement/" in url:
        return "stakeholder_project", "medium"
    if "safety approval" in combined:
        return "safety_approval", "high"
    if "experimental permit" in combined or "permit" in combined:
        return "experimental_permit", "high"
    if "vehicle operator license" in combined or "license" in combined:
        return "vehicle_operator_license", "high"
    return "faa_space_page", "medium"


def normalize_faa_matches(
    raw_pages: list[dict],
    *,
    companies: list[CompanyRecord],
    systems: list[SystemRecord],
) -> list[dict]:
    """Normalize FAA page matches to tracked companies and systems."""
    system_by_ticker: dict[str, list[SystemRecord]] = {}
    for system in systems:
        system_by_ticker.setdefault(system.ticker.upper(), []).append(system)

    records: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for company in companies:
        ticker = company.ticker.upper()
        company_systems = system_by_ticker.get(ticker, [])
        keywords = _unique_keywords(
            [company.company_name]
            + [system.system_name for system in company_systems if system.system_name]
        )

        for page in raw_pages:
            combined = f"{page.get('title', '')} {page.get('text', '')}"
            for keyword in keywords:
                if not _row_matches(combined, keyword):
                    continue
                matched_system = next(
                    (
                        system.system_name
                        for system in company_systems
                        if _normalize_text(system.system_name) == _normalize_text(keyword)
                    ),
                    "",
                )
                signal_type, priority = _infer_signal_type(page.get("url", ""), page.get("title", ""), page.get("text", ""))
                key = (ticker, page.get("url", ""), keyword)
                if key in seen:
                    continue
                seen.add(key)
                records.append(
                    {
                        "company_name": company.company_name,
                        "ticker": company.ticker,
                        "cik": company.cik,
                        "system_name": matched_system,
                        "matched_keyword": keyword,
                        "signal_type": signal_type,
                        "priority": priority,
                        "title": page.get("title", ""),
                        "summary_snippet": _extract_snippet(page.get("text", ""), keyword),
                        "status": "proposed" if "proposed" in _normalize_text(page.get("text", "")) else "",
                        "page_last_updated": page.get("last_updated", ""),
                        "source_url": page.get("url", ""),
                        "source_type": "FAA official page",
                        "source_confidence": "primary",
                        "fetched_at": page.get("fetched_at", ""),
                    }
                )

    return sorted(records, key=lambda record: (record["ticker"], record["source_url"], record["matched_keyword"]))


def save_faa_signals(records: list[dict], *, label: str = "watchlist") -> Path:
    """Persist normalized FAA signals."""
    destination = ensure_directory(PROCESSED_FAA_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = destination / f"faa_signals_{slugify(label)}_{timestamp}.json"
    write_json(out_path, records)
    return out_path
