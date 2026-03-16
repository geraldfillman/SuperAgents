"""SAM.gov opportunities adapter for pre-award pipeline tracking."""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

from .io_utils import write_json
from .paths import ensure_directory, project_path, slugify
from .watchlist import CompanyRecord, SystemRecord

SAM_API_BASE_URL = os.getenv("SAM_API_BASE_URL", "https://api.sam.gov/opportunities/v2")
SAM_TIMEOUT_SECONDS = float(os.getenv("SAM_TIMEOUT_SECONDS", "30"))
SAM_USER_AGENT = os.getenv(
    "SAM_USER_AGENT",
    os.getenv("SEC_EDGAR_USER_AGENT", "AerospaceDefenseTracker research@example.com"),
)
SAM_SEARCH_PATH = "/search"
SAM_PUBLIC_NOTICE_URL = "https://sam.gov/opp/{notice_id}/view"

RAW_SAM_QUERY_DIR = project_path("data", "raw", "sam", "queries")
RAW_SAM_RESULTS_DIR = project_path("data", "raw", "sam", "opportunities")
PROCESSED_PIPELINE_DIR = project_path("data", "processed", "pipeline_signals")

GENERIC_SYSTEM_TERMS = {
    "aircraft",
    "data",
    "mission",
    "platform",
    "services",
    "software",
    "support",
    "system",
    "systems",
    "vehicle",
}


def _make_client(api_key: str | None = None) -> httpx.Client:
    headers = {"User-Agent": SAM_USER_AGENT, "Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    return httpx.Client(
        base_url=SAM_API_BASE_URL,
        headers=headers,
        timeout=SAM_TIMEOUT_SECONDS,
        follow_redirects=True,
    )


def _normalize_text(value: str) -> str:
    lowered = "".join(char.lower() if char.isalnum() or char.isspace() else " " for char in value)
    return " ".join(lowered.split())


def _phrase_is_useful(value: str) -> bool:
    tokens = _normalize_text(value).split()
    if not tokens:
        return False
    return any(token not in GENERIC_SYSTEM_TERMS and len(token) > 2 for token in tokens)


def _unique_phrases(values: list[str]) -> list[str]:
    seen: set[str] = set()
    phrases: list[str] = []
    for value in values:
        phrase = value.strip()
        normalized = _normalize_text(phrase)
        if not phrase or not _phrase_is_useful(phrase) or normalized in seen:
            continue
        seen.add(normalized)
        phrases.append(phrase)
    return phrases


def build_sam_query_manifest(
    company: CompanyRecord,
    *,
    systems: list[SystemRecord] | None = None,
    days: int = 30,
    agency: str | None = None,
) -> dict:
    """Build a query manifest for SAM opportunities relevant to a company."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    system_rows = systems or []

    company_queries = [company.company_name] if company.company_name else []
    system_queries = [system.system_name for system in system_rows if system.system_name]
    type_queries = [system.system_type for system in system_rows if system.system_type]
    queries = _unique_phrases(company_queries + system_queries + type_queries)

    return {
        "company": asdict(company),
        "systems": [system.to_dict() for system in system_rows],
        "agency_filter": agency or "",
        "posted_from": start_date.isoformat(),
        "posted_to": end_date.isoformat(),
        "queries": [
            {
                "keyword": keyword,
                "system_name": next(
                    (system.system_name for system in system_rows if _normalize_text(system.system_name) == _normalize_text(keyword)),
                    "",
                ),
            }
            for keyword in queries
        ],
        "source_url": f"{SAM_API_BASE_URL}{SAM_SEARCH_PATH}",
        "generated_at": datetime.now().isoformat(),
    }


def save_sam_query_manifest(manifest: dict, *, label: str | None = None) -> Path:
    """Persist a SAM opportunity query manifest."""
    destination = ensure_directory(RAW_SAM_QUERY_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_label = label or manifest.get("company", {}).get("ticker") or manifest.get("company", {}).get("company_name") or "query"
    out_path = destination / f"sam_query_{slugify(manifest_label)}_{timestamp}.json"
    write_json(out_path, manifest)
    return out_path


def _extract_records(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("opportunitiesData", "data", "results", "opportunities"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            return [row for row in candidate if isinstance(row, dict)]

    for value in payload.values():
        if isinstance(value, list) and all(isinstance(row, dict) for row in value):
            return value
    return []


def _first_value(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in ("", None):
            return str(value)
    return ""


def _infer_priority(notice_type: str) -> str:
    normalized = _normalize_text(notice_type)
    if "solicitation" in normalized or "combined synopsis" in normalized:
        return "high"
    if "sources sought" in normalized or "presolicitation" in normalized:
        return "medium"
    return "low"


def fetch_sam_opportunity_pages(
    query: dict,
    *,
    api_key: str,
    page_size: int = 100,
    max_pages: int = 3,
    client: httpx.Client | None = None,
) -> list[dict]:
    """Fetch SAM opportunities for a query manifest row."""
    own_client = client is None
    if own_client:
        client = _make_client(api_key)

    raw_pages: list[dict] = []
    try:
        assert client is not None
        for page_index in range(max_pages):
            params = {
                "api_key": api_key,
                "postedFrom": query["posted_from"],
                "postedTo": query["posted_to"],
                "keyword": query["keyword"],
                "limit": page_size,
                "offset": page_index * page_size,
            }
            response = client.get(SAM_SEARCH_PATH, params=params)
            response.raise_for_status()
            payload = response.json()
            records = _extract_records(payload)
            raw_pages.append(
                {
                    "query": query,
                    "request": params,
                    "page": page_index + 1,
                    "response": payload,
                    "row_count": len(records),
                    "fetched_at": datetime.now().isoformat(),
                }
            )
            if len(records) < page_size:
                break
    finally:
        if own_client:
            client.close()

    return raw_pages


def _row_matches_query(row: dict, query: dict) -> bool:
    searchable = _normalize_text(
        " ".join(
            [
                _first_value(row, "title", "opportunityTitle"),
                _first_value(row, "description", "descriptionText"),
            ]
        )
    )
    keyword = _normalize_text(query.get("keyword", ""))
    if not keyword:
        return False
    if keyword in searchable:
        return True

    keyword_tokens = keyword.split()
    searchable_tokens = set(searchable.split())
    return bool(keyword_tokens) and all(token in searchable_tokens for token in keyword_tokens)


def normalize_sam_opportunity(row: dict, query: dict, company: CompanyRecord) -> dict:
    """Convert a SAM opportunity row into a normalized pipeline signal."""
    notice_id = _first_value(row, "noticeId", "notice_id")
    notice_type = _first_value(row, "type", "noticeType", "notice_type")
    title = _first_value(row, "title", "opportunityTitle")
    agency = _first_value(row, "fullParentPathName", "organizationName", "department")
    office_name = _first_value(row, "office", "subTier", "organizationHierarchy")
    source_url = SAM_PUBLIC_NOTICE_URL.format(notice_id=notice_id) if notice_id else f"{SAM_API_BASE_URL}{SAM_SEARCH_PATH}"

    return {
        "company_name": company.company_name,
        "ticker": company.ticker,
        "cik": company.cik,
        "ueid": company.ueid,
        "system_name": query.get("system_name", ""),
        "matched_keyword": query.get("keyword", ""),
        "notice_id": notice_id,
        "solicitation_number": _first_value(row, "solicitationNumber", "solicitation_number", "solicitationNo"),
        "title": title,
        "notice_type": notice_type,
        "priority": _infer_priority(notice_type),
        "status": "open" if _first_value(row, "active", "isActive").lower() in {"1", "true", "yes"} else "",
        "posted_date": _first_value(row, "postedDate", "posted_date", "publishDate"),
        "response_deadline": _first_value(row, "responseDeadLine", "responseDeadline", "response_deadline"),
        "archive_date": _first_value(row, "archiveDate", "archive_date"),
        "agency": agency,
        "office_name": office_name,
        "naics_code": _first_value(row, "naicsCode", "naics"),
        "set_aside": _first_value(row, "setAsideDescription", "setAside", "set_aside"),
        "description": _first_value(row, "description", "descriptionText"),
        "source_url": source_url,
        "source_type": "SAM.gov opportunities API",
        "source_confidence": "primary",
        "fetched_at": datetime.now().isoformat(),
    }


def save_raw_sam_pages(raw_pages: list[dict], *, label: str = "watchlist") -> Path:
    """Persist raw SAM opportunity pages."""
    destination = ensure_directory(RAW_SAM_RESULTS_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = destination / f"sam_opportunities_{slugify(label)}_{timestamp}.json"
    write_json(out_path, raw_pages)
    return out_path


def save_normalized_pipeline_signals(records: list[dict], *, label: str = "watchlist") -> Path:
    """Persist normalized SAM pipeline signals."""
    destination = ensure_directory(PROCESSED_PIPELINE_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = destination / f"pipeline_signals_{slugify(label)}_{timestamp}.json"
    write_json(out_path, records)
    return out_path


def normalize_pipeline_results(raw_pages: list[dict], company: CompanyRecord) -> list[dict]:
    """Flatten raw SAM pages into normalized pipeline signal records."""
    records: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for page in raw_pages:
        query = page.get("query", {})
        for row in _extract_records(page.get("response")):
            if not _row_matches_query(row, query):
                continue
            record = normalize_sam_opportunity(row, query, company)
            key = (record["ticker"], record["notice_id"], record["matched_keyword"])
            if key in seen:
                continue
            seen.add(key)
            records.append(record)
    return records
