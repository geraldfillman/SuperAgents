"""SEC companyfacts helpers for runway estimation."""

from __future__ import annotations

import os
import re
import time
from datetime import date, datetime
from pathlib import Path
import httpx

from .io_utils import load_json_records, write_json
from .paths import ensure_directory, project_path, slugify
from .sec import (
    SEC_SUBMISSIONS_BASE_URL,
    SEC_TIMEOUT_SECONDS,
    SEC_USER_AGENT,
    build_recent_filings,
    fetch_submissions,
    normalize_cik,
    resolve_cik,
)
from .watchlist import CompanyRecord, load_company_watchlist

SEC_COMPANYFACTS_BASE_URL = os.getenv("SEC_COMPANYFACTS_BASE_URL", "https://data.sec.gov/api/xbrl/companyfacts")
COMPANYFACTS_DIR = project_path("data", "raw", "sec", "companyfacts")
FINANCIALS_DIR = project_path("data", "processed", "financials")

CASH_CONCEPTS = (
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
)
SHORT_TERM_INVESTMENT_CONCEPTS = (
    "AvailableForSaleSecuritiesCurrent",
    "ShortTermInvestments",
    "MarketableSecuritiesCurrent",
)
OPERATING_CASHFLOW_CONCEPTS = (
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
)
GOING_CONCERN_PATTERNS = (
    r"substantial doubt about (?:our|the company'?s) ability to continue as a going concern",
    r"continue as a going concern",
)


def _make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": SEC_USER_AGENT, "Accept": "application/json"},
        timeout=SEC_TIMEOUT_SECONDS,
        follow_redirects=True,
    )


def fetch_companyfacts(cik_padded: str, client: httpx.Client | None = None) -> dict:
    """Fetch SEC XBRL companyfacts JSON."""
    own_client = client is None
    if own_client:
        client = _make_client()

    try:
        assert client is not None
        response = client.get(f"{SEC_COMPANYFACTS_BASE_URL}/CIK{cik_padded}.json")
        response.raise_for_status()
        return response.json()
    finally:
        if own_client:
            client.close()


def save_companyfacts_cache(cik_padded: str, payload: dict) -> Path:
    """Persist raw companyfacts JSON."""
    destination = ensure_directory(COMPANYFACTS_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = destination / f"companyfacts_{cik_padded}_{timestamp}.json"
    write_json(out_path, payload)
    return out_path


def _fact_end_date(fact: dict) -> date | None:
    raw = fact.get("end", "")
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _fact_filed_date(fact: dict) -> date | None:
    raw = fact.get("filed", "")
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _load_usd_facts(companyfacts: dict, concept: str) -> list[dict]:
    return companyfacts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get("USD", [])


def _best_instant_fact(companyfacts: dict, concepts: tuple[str, ...]) -> dict | None:
    candidates: list[dict] = []
    for concept in concepts:
        for fact in _load_usd_facts(companyfacts, concept):
            if fact.get("form") not in {"10-Q", "10-K"}:
                continue
            if not fact.get("end"):
                continue
            candidates.append({**fact, "_concept": concept})

    if not candidates:
        return None
    candidates.sort(
        key=lambda fact: (
            _fact_end_date(fact) or date.min,
            _fact_filed_date(fact) or date.min,
            fact.get("fy", 0),
        ),
        reverse=True,
    )
    return candidates[0]


def _best_duration_fact(companyfacts: dict, concepts: tuple[str, ...]) -> dict | None:
    candidates: list[dict] = []
    for concept in concepts:
        for fact in _load_usd_facts(companyfacts, concept):
            if fact.get("form") not in {"10-Q", "10-K"}:
                continue
            if not fact.get("start") or not fact.get("end"):
                continue
            candidates.append({**fact, "_concept": concept})

    if not candidates:
        return None
    candidates.sort(
        key=lambda fact: (
            _fact_end_date(fact) or date.min,
            _fact_filed_date(fact) or date.min,
            fact.get("fy", 0),
        ),
        reverse=True,
    )
    return candidates[0]


def _sum_liquidity(companyfacts: dict) -> tuple[float | None, dict]:
    cash_fact = _best_instant_fact(companyfacts, CASH_CONCEPTS)
    if cash_fact is None:
        return None, {}

    report_end = cash_fact.get("end", "")
    total_value = float(cash_fact.get("val", 0.0))
    components = {"cash_concept": cash_fact["_concept"]}

    st_fact = _best_instant_fact(companyfacts, SHORT_TERM_INVESTMENT_CONCEPTS)
    if st_fact is not None and st_fact.get("end") == report_end:
        total_value += float(st_fact.get("val", 0.0))
        components["short_term_investment_concept"] = st_fact["_concept"]

    return total_value / 1_000_000, {
        **components,
        "report_date": report_end,
        "form_type": cash_fact.get("form", ""),
        "accession_number": cash_fact.get("accn", ""),
    }


def _quarterly_burn_millions(companyfacts: dict) -> tuple[float | None, dict]:
    burn_fact = _best_duration_fact(companyfacts, OPERATING_CASHFLOW_CONCEPTS)
    if burn_fact is None:
        return None, {}

    start = date.fromisoformat(burn_fact["start"])
    end = date.fromisoformat(burn_fact["end"])
    duration_days = max((end - start).days + 1, 1)
    raw_value = float(burn_fact.get("val", 0.0))
    quarterly_value = raw_value * (90.0 / duration_days)
    burn_value = max(0.0, -quarterly_value) / 1_000_000

    return burn_value, {
        "cashflow_concept": burn_fact["_concept"],
        "cashflow_duration_days": duration_days,
        "cashflow_accession_number": burn_fact.get("accn", ""),
    }


def _estimate_runway_months(total_cash_millions: float | None, quarterly_burn_millions: float | None) -> float | None:
    if total_cash_millions is None or quarterly_burn_millions is None:
        return None
    if quarterly_burn_millions <= 0:
        return None
    return round((total_cash_millions / quarterly_burn_millions) * 3, 1)


def _find_source_url(submissions: dict, accession_number: str) -> str:
    if not accession_number:
        return ""
    accession_key = accession_number.replace("-", "")
    for filing in build_recent_filings(submissions, filing_types=("10-Q", "10-K"), limit=40):
        if filing.get("accession_number", "").replace("-", "") == accession_key:
            return filing.get("filing_url", "")
    cik_unpadded, _ = normalize_cik(str(submissions.get("cik", "")))
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    primary_documents = recent.get("primaryDocument", [])
    for index, accession in enumerate(accessions):
        if accession.replace("-", "") == accession_key and index < len(primary_documents):
            return f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession_key}/{primary_documents[index]}"
    return f"{SEC_SUBMISSIONS_BASE_URL}/CIK{normalize_cik(str(submissions.get('cik', '')))[1]}.json"


def _going_concern_flag_from_cached_filings(ticker: str) -> bool:
    filings_dir = project_path("data", "raw", "sec", "filings_text")
    pattern = f"{slugify(ticker)}_*.txt"
    files = sorted(filings_dir.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in files[:5]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lowered = text.lower()
        if any(re.search(pattern, lowered) for pattern in GOING_CONCERN_PATTERNS):
            return True
    return False


def build_financial_snapshot(
    *,
    ticker: str,
    company_name: str,
    cik_padded: str,
    companyfacts: dict,
    submissions: dict,
) -> dict:
    """Build a normalized financial snapshot."""
    total_cash_millions, liquidity_meta = _sum_liquidity(companyfacts)
    quarterly_burn_millions, burn_meta = _quarterly_burn_millions(companyfacts)
    accession_number = burn_meta.get("cashflow_accession_number") or liquidity_meta.get("accession_number", "")
    report_date = liquidity_meta.get("report_date") or ""
    form_type = liquidity_meta.get("form_type") or ""

    return {
        "company_name": company_name,
        "ticker": ticker,
        "cik": cik_padded,
        "report_date": report_date,
        "form_type": form_type,
        "total_cash_millions": round(total_cash_millions, 1) if total_cash_millions is not None else None,
        "quarterly_burn_millions": round(quarterly_burn_millions, 1) if quarterly_burn_millions is not None else None,
        "est_runway_months": _estimate_runway_months(total_cash_millions, quarterly_burn_millions),
        "going_concern_flag": _going_concern_flag_from_cached_filings(ticker),
        "source_url": _find_source_url(submissions, accession_number),
        "source_type": "SEC companyfacts",
        "source_confidence": "primary",
        "supporting_metadata": {
            **liquidity_meta,
            **burn_meta,
        },
        "fetched_at": datetime.now().isoformat(),
    }


def save_financial_snapshot(snapshot: dict) -> Path:
    """Write a normalized financial snapshot."""
    destination = ensure_directory(FINANCIALS_DIR)
    label = slugify(f"{snapshot.get('ticker', '')}_{snapshot.get('report_date', '')}")
    out_path = destination / f"financials_{label}.json"
    write_json(out_path, snapshot)
    return out_path


def load_latest_financial_snapshots(processed_root: Path | None = None) -> dict[str, dict]:
    """Load the latest saved financial snapshot for each ticker."""
    root = processed_root or FINANCIALS_DIR
    latest: dict[str, dict] = {}
    for record in load_json_records(root):
        ticker = str(record.get("ticker", "")).upper()
        if not ticker:
            continue
        current = latest.get(ticker)
        candidate_key = (str(record.get("report_date", "")), str(record.get("fetched_at", "")))
        if current is None or candidate_key > (
            str(current.get("report_date", "")),
            str(current.get("fetched_at", "")),
        ):
            latest[ticker] = record
    return latest


def fetch_and_build_financial_snapshot(
    *,
    cik: str | None = None,
    ticker: str | None = None,
    client: httpx.Client | None = None,
) -> dict:
    """Fetch companyfacts plus submissions and build a normalized snapshot."""
    own_client = client is None
    if own_client:
        client = _make_client()

    try:
        assert client is not None
        cik_padded = resolve_cik(cik=cik, ticker=ticker, client=client)
        companyfacts = fetch_companyfacts(cik_padded, client=client)
        save_companyfacts_cache(cik_padded, companyfacts)
        submissions = fetch_submissions(cik_padded, client=client)
        resolved_ticker = ticker or (submissions.get("tickers") or [""])[0]
        snapshot = build_financial_snapshot(
            ticker=resolved_ticker,
            company_name=companyfacts.get("entityName", submissions.get("name", "")),
            cik_padded=cik_padded,
            companyfacts=companyfacts,
            submissions=submissions,
        )
        out_path = save_financial_snapshot(snapshot)
    finally:
        if own_client:
            client.close()

    return {**snapshot, "output_path": str(out_path)}


def fetch_watchlist_financial_snapshots(
    *,
    companies: list[CompanyRecord] | None = None,
    only_missing: bool = False,
    limit: int | None = None,
    pause_seconds: float = 0.2,
    processed_root: Path | None = None,
    client: httpx.Client | None = None,
) -> dict:
    """Fetch financial snapshots across the tracked watchlist."""
    own_client = client is None
    if own_client:
        client = _make_client()

    company_rows = [company for company in (companies or load_company_watchlist()) if company.ticker]
    if limit is not None:
        company_rows = company_rows[:limit]

    existing = load_latest_financial_snapshots(processed_root)
    snapshots: list[dict] = []
    skipped: list[dict] = []
    failures: list[dict] = []

    try:
        assert client is not None
        for index, company in enumerate(company_rows):
            ticker = company.ticker.upper()
            if only_missing and ticker in existing:
                skipped.append(
                    {
                        "ticker": ticker,
                        "reason": "existing_snapshot",
                        "report_date": existing[ticker].get("report_date", ""),
                    }
                )
                continue

            try:
                snapshot = fetch_and_build_financial_snapshot(
                    cik=company.cik or None,
                    ticker=ticker,
                    client=client,
                )
            except Exception as exc:
                failures.append({"ticker": ticker, "error": str(exc)})
            else:
                snapshots.append(snapshot)

            if pause_seconds > 0 and index < (len(company_rows) - 1):
                time.sleep(pause_seconds)
    finally:
        if own_client:
            client.close()

    return {
        "fetched_at": datetime.now().isoformat(),
        "requested_companies": len(company_rows),
        "saved_snapshots": len(snapshots),
        "skipped_count": len(skipped),
        "failure_count": len(failures),
        "snapshots": snapshots,
        "skipped": skipped,
        "failures": failures,
    }
