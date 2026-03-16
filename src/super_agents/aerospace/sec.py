"""SEC submissions and filing-text helpers."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import httpx

from .io_utils import read_json, write_json
from .paths import ensure_directory, project_path, slugify

SEC_SUBMISSIONS_BASE_URL = "https://data.sec.gov/submissions"
SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "AerospaceDefenseTracker research@example.com")
SEC_TIMEOUT_SECONDS = float(os.getenv("SEC_TIMEOUT_SECONDS", "30"))

SEC_REFERENCE_DIR = project_path("data", "raw", "sec", "reference")
SEC_SUBMISSIONS_DIR = project_path("data", "raw", "sec", "submissions")
SEC_FILINGS_DIR = project_path("data", "raw", "sec", "filings_text")


def normalize_cik(cik: str) -> tuple[str, str]:
    """Return unpadded and padded CIK values."""
    digits = "".join(char for char in str(cik) if char.isdigit())
    if not digits:
        raise ValueError("CIK must contain at least one digit")

    cik_unpadded = digits.lstrip("0") or "0"
    cik_padded = cik_unpadded.zfill(10)
    return cik_unpadded, cik_padded


def _make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": SEC_USER_AGENT, "Accept": "application/json"},
        timeout=SEC_TIMEOUT_SECONDS,
        follow_redirects=True,
    )


def fetch_ticker_map(*, force_refresh: bool = False, client: httpx.Client | None = None) -> dict[str, str]:
    """Fetch or load the SEC ticker-to-CIK mapping."""
    cache_path = ensure_directory(SEC_REFERENCE_DIR) / "company_tickers.json"
    if cache_path.exists() and not force_refresh:
        raw_mapping = read_json(cache_path)
    else:
        own_client = client is None
        if own_client:
            client = _make_client()
        try:
            assert client is not None
            response = client.get(SEC_TICKER_MAP_URL)
            response.raise_for_status()
            raw_mapping = response.json()
        finally:
            if own_client:
                client.close()
        write_json(cache_path, raw_mapping)

    ticker_map: dict[str, str] = {}
    for row in raw_mapping.values():
        ticker = str(row.get("ticker", "")).upper()
        cik_str = str(row.get("cik_str", ""))
        if not ticker or not cik_str:
            continue
        ticker_map[ticker] = normalize_cik(cik_str)[1]
    return ticker_map


def resolve_cik(
    *,
    cik: str | None = None,
    ticker: str | None = None,
    force_refresh_ticker_map: bool = False,
    client: httpx.Client | None = None,
) -> str:
    """Resolve a padded CIK from explicit input or from the SEC ticker map."""
    if cik:
        return normalize_cik(cik)[1]
    if not ticker:
        raise ValueError("Provide either a CIK or a ticker.")

    ticker_map = fetch_ticker_map(force_refresh=force_refresh_ticker_map, client=client)
    resolved = ticker_map.get(ticker.upper())
    if not resolved:
        raise ValueError(f"No SEC CIK mapping was found for ticker {ticker.upper()}.")
    return resolved


def fetch_submissions(cik_padded: str, client: httpx.Client | None = None) -> dict:
    """Fetch SEC company submissions JSON."""
    own_client = client is None
    if own_client:
        client = _make_client()

    try:
        assert client is not None
        response = client.get(f"{SEC_SUBMISSIONS_BASE_URL}/CIK{cik_padded}.json")
        response.raise_for_status()
        return response.json()
    finally:
        if own_client:
            client.close()


def save_submissions_cache(cik_padded: str, submissions: dict) -> Path:
    """Save the raw submissions JSON."""
    destination = ensure_directory(SEC_SUBMISSIONS_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = destination / f"submissions_{cik_padded}_{timestamp}.json"
    write_json(out_path, submissions)
    return out_path


def build_recent_filings(
    submissions: dict,
    *,
    filing_types: tuple[str, ...] = ("8-K", "10-Q", "10-K"),
    limit: int = 5,
) -> list[dict]:
    """Build recent filing records from SEC submissions JSON."""
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_documents = recent.get("primaryDocument", [])

    cik_unpadded, cik_padded = normalize_cik(str(submissions.get("cik", "")))
    records: list[dict] = []
    for index, form_type in enumerate(forms):
        if form_type not in filing_types:
            continue
        if len(records) >= limit:
            break

        accession_number = accessions[index]
        accession = accession_number.replace("-", "")
        primary_document = primary_documents[index]
        records.append(
            {
                "cik": cik_padded,
                "ticker": ",".join(submissions.get("tickers", [])),
                "company_name": submissions.get("name", ""),
                "form_type": form_type,
                "filing_date": dates[index] if index < len(dates) else "",
                "accession_number": accession_number,
                "primary_document": primary_document,
                "filing_url": (
                    f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession}/{primary_document}"
                ),
            }
        )
    return records


def fetch_filing_text(filing: dict, client: httpx.Client | None = None) -> str:
    """Fetch a filing document as plain text."""
    own_client = client is None
    if own_client:
        client = _make_client()

    try:
        assert client is not None
        response = client.get(filing["filing_url"], headers={"User-Agent": SEC_USER_AGENT})
        response.raise_for_status()
        return response.text
    finally:
        if own_client:
            client.close()


def save_filing_text(filing: dict, text: str) -> Path:
    """Save filing text to the local raw cache."""
    destination = ensure_directory(SEC_FILINGS_DIR)
    label = slugify(f"{filing.get('ticker', '')}_{filing['form_type']}_{filing['filing_date']}")
    accession = filing.get("accession_number", "").replace("-", "") or "filing"
    out_path = destination / f"{label}_{accession}.txt"
    out_path.write_text(text, encoding="utf-8")
    return out_path


def fetch_and_cache_sec_filings(
    *,
    cik: str | None = None,
    ticker: str | None = None,
    filing_types: tuple[str, ...] = ("8-K", "10-Q", "10-K"),
    limit: int = 5,
    force_refresh_ticker_map: bool = False,
    client: httpx.Client | None = None,
) -> dict:
    """Resolve a company, fetch recent filings, and cache submissions plus text."""
    own_client = client is None
    if own_client:
        client = _make_client()

    try:
        assert client is not None
        cik_padded = resolve_cik(
            cik=cik,
            ticker=ticker,
            force_refresh_ticker_map=force_refresh_ticker_map,
            client=client,
        )
        submissions = fetch_submissions(cik_padded, client=client)
        submissions_path = save_submissions_cache(cik_padded, submissions)
        filings = build_recent_filings(submissions, filing_types=filing_types, limit=limit)

        cached_filings: list[dict] = []
        for filing in filings:
            text = fetch_filing_text(filing, client=client)
            text_path = save_filing_text(filing, text)
            cached_filings.append({**filing, "text_path": str(text_path)})

        label = slugify(ticker or submissions.get("tickers", [""])[0] or submissions.get("name", cik_padded))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        manifest_path = ensure_directory(SEC_SUBMISSIONS_DIR) / f"filing_manifest_{label}_{timestamp}.json"
        write_json(
            manifest_path,
            {
                "ticker": ",".join(submissions.get("tickers", [])),
                "company_name": submissions.get("name", ""),
                "cik": cik_padded,
                "filing_types": list(filing_types),
                "filings": cached_filings,
            },
        )
    finally:
        if own_client:
            client.close()

    return {
        "cik": cik_padded,
        "submissions_path": str(submissions_path),
        "manifest_path": str(manifest_path),
        "filings": cached_filings,
    }


def find_latest_filing_manifest(ticker: str) -> Path | None:
    """Return the latest cached filing manifest for a ticker when present."""
    pattern = f"filing_manifest_{slugify(ticker)}_*.json"
    manifests = sorted(SEC_SUBMISSIONS_DIR.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not manifests:
        return None
    return manifests[-1]
