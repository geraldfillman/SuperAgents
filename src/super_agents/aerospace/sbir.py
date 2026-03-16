"""SBIR award-search adapter for small-cap and microcap coverage."""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import time

import httpx

from .io_utils import write_json
from .paths import ensure_directory, project_path, slugify
from .watchlist import CompanyRecord

SBIR_API_BASE_URL = os.getenv("SBIR_API_BASE_URL", "https://api.www.sbir.gov/public/api")
SBIR_TIMEOUT_SECONDS = float(os.getenv("SBIR_TIMEOUT_SECONDS", "30"))
SBIR_USER_AGENT = os.getenv(
    "SBIR_USER_AGENT",
    os.getenv("SEC_EDGAR_USER_AGENT", "AerospaceDefenseTracker research@example.com"),
)
SBIR_AWARDS_PATH = "/awards"
SBIR_AWARDS_PUBLIC_URL = "https://www.sbir.gov/awards"

RAW_SBIR_DIR = project_path("data", "raw", "sbir", "awards")
RAW_SBIR_QUERY_DIR = project_path("data", "raw", "sbir", "queries")
PROCESSED_SBIR_DIR = project_path("data", "processed", "sbir_awards")

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


def _make_client() -> httpx.Client:
    return httpx.Client(
        base_url=SBIR_API_BASE_URL,
        headers={"User-Agent": SBIR_USER_AGENT, "Accept": "application/json"},
        timeout=SBIR_TIMEOUT_SECONDS,
        follow_redirects=True,
    )


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


def _to_float(value: object) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def build_awards_params(
    *,
    firm: str | None = None,
    agency: str | None = None,
    year: int | None = None,
    rows: int = 100,
    start: int = 0,
) -> dict[str, object]:
    """Build a query-parameter dictionary for the SBIR awards API."""
    params: dict[str, object] = {
        "rows": rows,
        "start": start,
    }
    if firm:
        params["firm"] = firm
    if agency:
        params["agency"] = agency
    if year is not None:
        params["year"] = year
    return params


def build_sbir_query_manifest(
    company: CompanyRecord,
    *,
    agency: str | None = None,
    year: int | None = None,
    rows: int = 100,
) -> dict:
    """Build a saved query manifest for SBIR awards."""
    return {
        "company": asdict(company),
        "agency_filter": agency or "",
        "year_filter": year,
        "rows": rows,
        "source_url": f"{SBIR_API_BASE_URL}{SBIR_AWARDS_PATH}",
        "generated_at": datetime.now().isoformat(),
    }


def save_sbir_query_manifest(manifest: dict, *, label: str | None = None) -> Path:
    """Persist an SBIR query manifest."""
    destination = ensure_directory(RAW_SBIR_QUERY_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_label = label or manifest.get("company", {}).get("ticker") or manifest.get("company", {}).get("company_name") or "query"
    out_path = destination / f"sbir_query_{slugify(manifest_label)}_{timestamp}.json"
    write_json(out_path, manifest)
    return out_path


def _extract_award_rows(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("results", "data", "awards", "response"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            return [row for row in candidate if isinstance(row, dict)]

    for value in payload.values():
        if isinstance(value, list) and all(isinstance(row, dict) for row in value):
            return value
    return []


def fetch_sbir_award_pages(
    *,
    firm: str | None = None,
    agency: str | None = None,
    year: int | None = None,
    rows: int = 100,
    max_pages: int = 5,
    client: httpx.Client | None = None,
) -> list[dict]:
    """Fetch SBIR award pages using firm, agency, and optional year filters."""
    own_client = client is None
    if own_client:
        client = _make_client()

    raw_pages: list[dict] = []
    try:
        assert client is not None
        for page_index in range(max_pages):
            params = build_awards_params(
                firm=firm,
                agency=agency,
                year=year,
                rows=rows,
                start=page_index * rows,
            )
            payload: object | None = None
            last_response: httpx.Response | None = None
            for attempt in range(3):
                response = client.get(SBIR_AWARDS_PATH, params=params)
                last_response = response
                if response.status_code == 429 and attempt < 2:
                    retry_after = response.headers.get("Retry-After", "1")
                    try:
                        sleep_seconds = min(float(retry_after), 5.0)
                    except ValueError:
                        sleep_seconds = 1.0
                    time.sleep(max(sleep_seconds, 0.5))
                    continue
                response.raise_for_status()
                payload = response.json()
                break

            if payload is None:
                assert last_response is not None
                last_response.raise_for_status()
                raise RuntimeError("SBIR award fetch failed before a payload was returned.")

            rows_payload = _extract_award_rows(payload)
            raw_pages.append(
                {
                    "query": params,
                    "page": page_index + 1,
                    "response": payload,
                    "row_count": len(rows_payload),
                    "fetched_at": datetime.now().isoformat(),
                }
            )
            if len(rows_payload) < rows:
                break
    finally:
        if own_client:
            client.close()

    return raw_pages


def company_matches_sbir_award(company: CompanyRecord, row: dict) -> bool:
    """Return True when an SBIR award row appears to belong to the tracked company."""
    if company.ueid and str(row.get("uei", "")).strip().upper() == company.ueid.strip().upper():
        return True

    firm_name = str(row.get("firm", ""))
    if not firm_name:
        return False

    normalized_company = _normalize_text(company.company_name)
    normalized_firm = _normalize_text(firm_name)
    if normalized_company and normalized_company in normalized_firm:
        return True
    if normalized_firm and normalized_firm in normalized_company:
        return True

    company_tokens = _significant_tokens(company.company_name)
    firm_tokens = set(_significant_tokens(firm_name))
    return bool(company_tokens) and all(token in firm_tokens for token in company_tokens)


def match_sbir_awards_to_companies(raw_pages: list[dict], companies: list[CompanyRecord]) -> list[dict]:
    """Associate SBIR award rows with tracked companies."""
    matches: list[dict] = []
    seen_rows: set[tuple[str, str]] = set()

    for page in raw_pages:
        for row in _extract_award_rows(page.get("response")):
            row_key = (
                str(row.get("agency_tracking_number") or row.get("contract") or row.get("award_link") or ""),
                str(row.get("proposal_award_date", "")),
            )
            if not row_key[0]:
                continue

            for company in companies:
                if not company_matches_sbir_award(company, row):
                    continue
                scoped_key = (f"{row_key[0]}::{row_key[1]}", company.ticker)
                if scoped_key in seen_rows:
                    continue
                seen_rows.add(scoped_key)
                matches.append({"company": asdict(company), "award": row})

    return matches


def normalize_sbir_award_match(match: dict) -> dict:
    """Convert a matched SBIR award row into a normalized processed record."""
    company = match["company"]
    row = match["award"]
    award_amount = _to_float(row.get("award_amount"))

    return {
        "company_name": company["company_name"],
        "ticker": company["ticker"],
        "cik": company["cik"],
        "ueid": company["ueid"],
        "firm_name": row.get("firm", ""),
        "agency": row.get("agency", ""),
        "branch": row.get("branch", ""),
        "program": row.get("program", ""),
        "phase": row.get("phase", ""),
        "agency_tracking_number": row.get("agency_tracking_number", ""),
        "contract": row.get("contract", ""),
        "award_title": row.get("award_title", ""),
        "topic_code": row.get("topic_code", ""),
        "award_year": row.get("award_year"),
        "award_amount_usd": award_amount,
        "proposal_award_date": row.get("proposal_award_date", ""),
        "contract_end_date": row.get("contract_end_date", ""),
        "research_area_keywords": row.get("research_area_keywords", ""),
        "abstract": row.get("abstract", ""),
        "company_url": row.get("company_url", ""),
        "source_url": row.get("award_link") or SBIR_AWARDS_PUBLIC_URL,
        "source_type": "SBIR.gov award API",
        "source_confidence": "primary",
        "fetched_at": datetime.now().isoformat(),
    }


def save_raw_sbir_pages(raw_pages: list[dict], *, label: str = "awards") -> Path:
    """Persist raw SBIR award search pages."""
    destination = ensure_directory(RAW_SBIR_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = destination / f"sbir_awards_{slugify(label)}_{timestamp}.json"
    write_json(out_path, raw_pages)
    return out_path


def save_normalized_sbir_awards(records: list[dict], *, label: str = "watchlist") -> Path:
    """Persist normalized SBIR award records."""
    destination = ensure_directory(PROCESSED_SBIR_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = destination / f"sbir_awards_{slugify(label)}_{timestamp}.json"
    write_json(out_path, records)
    return out_path
