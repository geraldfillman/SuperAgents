"""USAspending award-search adapter."""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

from .io_utils import write_json
from .paths import ensure_directory, project_path, slugify
from .watchlist import CompanyRecord

USASPENDING_API_BASE_URL = os.getenv("USASPENDING_API_BASE_URL", "https://api.usaspending.gov")
USASPENDING_TIMEOUT_SECONDS = float(os.getenv("USASPENDING_TIMEOUT_SECONDS", "30"))
USASPENDING_USER_AGENT = os.getenv(
    "USASPENDING_USER_AGENT",
    os.getenv("SEC_EDGAR_USER_AGENT", "AerospaceDefenseTracker research@example.com"),
)

SEARCH_BY_AWARD_PATH = "/api/v2/search/spending_by_award/"
USASPENDING_AWARD_URL_TEMPLATE = "https://www.usaspending.gov/award/{generated_internal_id}/"

# Official source: https://api.usaspending.gov/api/v2/references/award_types/
CONTRACT_AWARD_CODES = ("A", "B", "C", "D")
IDV_AWARD_CODES = ("IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", "IDV_B_C", "IDV_C", "IDV_D", "IDV_E")

SEARCH_FIELDS = [
    "Award ID",
    "Recipient Name",
    "Start Date",
    "End Date",
    "Award Amount",
    "Awarding Agency",
    "Awarding Sub Agency",
    "Award Type",
    "Award Description",
]
SORT_FALLBACKS = ("Start Date", "Award Amount")

RAW_SEARCH_DIR = project_path("data", "raw", "awards", "usaspending")
PROCESSED_AWARD_DIR = project_path("data", "processed", "contract_awards")

CORPORATE_SUFFIXES = {
    "co",
    "company",
    "corp",
    "corporation",
    "group",
    "holdings",
    "inc",
    "incorporated",
    "limited",
    "llc",
    "ltd",
    "plc",
}


def _normalize_text(value: str) -> str:
    lowered = "".join(char.lower() if char.isalnum() or char.isspace() else " " for char in value)
    return " ".join(lowered.split())


def _significant_tokens(value: str) -> list[str]:
    tokens = []
    for token in _normalize_text(value).split():
        if len(token) <= 2 or token in CORPORATE_SUFFIXES:
            continue
        tokens.append(token)
    return tokens


def build_search_payload(
    *,
    days: int,
    award_type_codes: tuple[str, ...],
    page: int,
    limit: int,
    agency: str | None = None,
    sort: str = SORT_FALLBACKS[0],
) -> dict:
    """Build a USAspending award-search payload."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    filters: dict[str, object] = {
        "award_type_codes": list(award_type_codes),
        "time_period": [
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }
        ],
    }
    if agency:
        filters["agencies"] = [
            {"type": "awarding", "tier": "toptier", "name": agency},
            {"type": "awarding", "tier": "subtier", "name": agency},
        ]

    return {
        "filters": filters,
        "fields": SEARCH_FIELDS,
        "limit": limit,
        "page": page,
        "sort": sort,
        "order": "desc",
        "subawards": False,
    }


def _post_search_page(client: httpx.Client, payload: dict) -> dict:
    """POST a search payload with sort fallbacks."""
    last_error: httpx.HTTPStatusError | None = None
    for sort in SORT_FALLBACKS:
        candidate = {**payload, "sort": sort}
        response = client.post(SEARCH_BY_AWARD_PATH, json=candidate)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code == 422:
                continue
            raise
        return response.json()

    if last_error is not None:
        raise last_error
    raise RuntimeError("USAspending search failed before a response was returned.")


def fetch_award_search_pages(
    *,
    days: int,
    agency: str | None = None,
    page_size: int = 50,
    max_pages: int = 5,
    include_idvs: bool = True,
    client: httpx.Client | None = None,
) -> list[dict]:
    """Fetch recent contract and optional IDV award pages from USAspending."""
    own_client = client is None
    if own_client:
        client = httpx.Client(
            base_url=USASPENDING_API_BASE_URL,
            headers={"User-Agent": USASPENDING_USER_AGENT, "Accept": "application/json"},
            timeout=USASPENDING_TIMEOUT_SECONDS,
        )

    groups = [("contracts", CONTRACT_AWARD_CODES)]
    if include_idvs:
        groups.append(("idvs", IDV_AWARD_CODES))

    raw_pages: list[dict] = []
    try:
        assert client is not None
        for group_name, award_codes in groups:
            for page in range(1, max_pages + 1):
                payload = build_search_payload(
                    days=days,
                    agency=agency,
                    award_type_codes=award_codes,
                    page=page,
                    limit=page_size,
                )
                response_json = _post_search_page(client, payload)
                raw_pages.append(
                    {
                        "group": group_name,
                        "page": page,
                        "request": payload,
                        "response": response_json,
                        "fetched_at": datetime.now().isoformat(),
                    }
                )
                if not response_json.get("page_metadata", {}).get("hasNext"):
                    break
    finally:
        if own_client:
            client.close()

    return raw_pages


def company_matches_award(company: CompanyRecord, row: dict) -> bool:
    """Return True when an award row appears to belong to a tracked company."""
    recipient_name = row.get("Recipient Name", "")
    if not recipient_name:
        return False

    normalized_company = _normalize_text(company.company_name)
    normalized_recipient = _normalize_text(recipient_name)
    if normalized_company and normalized_company in normalized_recipient:
        return True
    if normalized_recipient and normalized_recipient in normalized_company:
        return True

    company_tokens = _significant_tokens(company.company_name)
    recipient_tokens = set(_significant_tokens(recipient_name))
    return bool(company_tokens) and all(token in recipient_tokens for token in company_tokens)


def match_awards_to_companies(raw_pages: list[dict], companies: list[CompanyRecord]) -> list[dict]:
    """Associate USAspending award rows with tracked companies."""
    matches: list[dict] = []
    seen_rows: set[tuple[str, str]] = set()

    for page in raw_pages:
        group_name = page["group"]
        for row in page.get("response", {}).get("results", []):
            award_key = (group_name, str(row.get("generated_internal_id") or row.get("Award ID") or ""))
            if not award_key[1]:
                continue

            for company in companies:
                if not company_matches_award(company, row):
                    continue
                scoped_key = (award_key[0], f"{award_key[1]}::{company.ticker}")
                if scoped_key in seen_rows:
                    continue
                seen_rows.add(scoped_key)
                matches.append(
                    {
                        "company": asdict(company),
                        "group": group_name,
                        "award": row,
                    }
                )

    return matches


def _award_status(end_date_value: str) -> str:
    if not end_date_value:
        return ""
    try:
        parsed = datetime.fromisoformat(end_date_value).date()
    except ValueError:
        return ""
    return "completed" if parsed < date.today() else "active"


def normalize_award_match(match: dict) -> dict:
    """Convert a matched award row into a contract_awards-style record."""
    company = match["company"]
    row = match["award"]
    generated_internal_id = row.get("generated_internal_id", "")
    award_amount = row.get("Award Amount")
    description = row.get("Award Description") or f"{row.get('Recipient Name', '')} | {row.get('Award ID', '')}".strip()

    return {
        "company_name": company["company_name"],
        "ticker": company["ticker"],
        "cik": company["cik"],
        "cage_code": company["cage_code"],
        "ueid": company["ueid"],
        "award_number": row.get("Award ID", ""),
        "agency": row.get("Awarding Agency", ""),
        "office_name": row.get("Awarding Sub Agency", ""),
        "vehicle_type": match["group"],
        "award_type": row.get("Award Type") or match["group"],
        "contract_status": _award_status(row.get("End Date", "")),
        "ceiling_value_usd": None,
        "obligated_value_usd": award_amount,
        "award_date": row.get("Start Date", ""),
        "start_date": row.get("Start Date", ""),
        "end_date": row.get("End Date", ""),
        "period_of_performance_text": " to ".join(
            part for part in [row.get("Start Date", ""), row.get("End Date", "")] if part
        ),
        "description": description,
        "matched_recipient_name": row.get("Recipient Name", ""),
        "source_url": (
            USASPENDING_AWARD_URL_TEMPLATE.format(generated_internal_id=generated_internal_id)
            if generated_internal_id else f"{USASPENDING_API_BASE_URL}{SEARCH_BY_AWARD_PATH}"
        ),
        "source_type": "USAspending",
        "source_confidence": "primary",
        "fetched_at": datetime.now().isoformat(),
    }


def save_raw_award_pages(raw_pages: list[dict], *, agency: str | None = None, label: str = "search") -> Path:
    """Persist raw USAspending pages for later inspection."""
    destination = ensure_directory(RAW_SEARCH_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    agency_slug = slugify(agency or "all_agencies")
    out_path = destination / f"usaspending_{label}_{agency_slug}_{timestamp}.json"
    write_json(out_path, raw_pages)
    return out_path


def save_normalized_awards(records: list[dict], *, agency: str | None = None, label: str = "awards") -> Path:
    """Persist normalized award records."""
    destination = ensure_directory(PROCESSED_AWARD_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    agency_slug = slugify(agency or "all_agencies")
    out_path = destination / f"contract_awards_{label}_{agency_slug}_{timestamp}.json"
    write_json(out_path, records)
    return out_path
