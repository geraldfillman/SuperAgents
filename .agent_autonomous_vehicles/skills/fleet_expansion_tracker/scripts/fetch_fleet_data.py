"""
Fleet Expansion Tracker -- Fetch Fleet Data
Search SEC EDGAR EFTS for 10-Q/8-K filings with fleet size, ride count,
and miles-driven disclosures.
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path("data/raw/autonomous_vehicles/fleet")
EDGAR_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
EDGAR_EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"

USER_AGENT = os.getenv(
    "SEC_EDGAR_USER_AGENT",
    "AVRoboticsTracker research@example.com",
)


def _normalize_cik(cik: str) -> tuple[str, str]:
    """Return (unpadded, zero-padded-to-10) CIK."""
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    if not digits:
        raise ValueError("CIK must contain at least one digit")
    unpadded = digits.lstrip("0") or "0"
    padded = digits.zfill(10)
    return unpadded, padded


def fetch_fleet_disclosures_efts(
    cik: str | None = None,
    days: int = 90,
    limit: int = 50,
) -> list[dict]:
    """
    Search EDGAR full-text for fleet size, ride count, and miles-driven
    disclosures in 10-Q and 8-K filings.

    Args:
        cik: Optional CIK to restrict search to a single company
        days: Lookback window in days
        limit: Max results
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT}
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    # Build query for fleet-related disclosures
    fleet_terms = (
        '("fleet size" OR "vehicles deployed" OR "ride count" '
        'OR "miles driven" OR "autonomous miles" OR "driverless miles" '
        'OR "operational domain" OR "commercial operations")'
    )
    av_terms = (
        '("autonomous" OR "self-driving" OR "driverless" '
        'OR "robotaxi" OR "autonomous trucking")'
    )
    query = f"{fleet_terms} AND {av_terms}"

    params = {
        "q": query,
        "dateRange": "custom",
        "startdt": start_date,
        "enddt": end_date,
        "forms": "8-K,10-Q,10-K",
    }

    response = httpx.get(
        EDGAR_EFTS_BASE, params=params, headers=headers, timeout=30
    )
    response.raise_for_status()
    data = response.json()

    hits = data.get("hits", {}).get("hits", [])[:limit]

    results: list[dict] = []
    for hit in hits:
        source = hit.get("_source", {})

        # If CIK filter specified, skip non-matching
        if cik:
            _, cik_padded = _normalize_cik(cik)
            entity_cik = str(source.get("entity_id", "")).zfill(10)
            if entity_cik != cik_padded:
                continue

        record = {
            "company_name": source.get("entity_name", ""),
            "cik": source.get("entity_id", ""),
            "filing_type": source.get("form_type", ""),
            "filing_date": source.get("file_date", ""),
            "filing_url": source.get("file_url", ""),
            "display_name": (
                source.get("display_names", [""])[0]
                if source.get("display_names")
                else ""
            ),
            "source_url": source.get("file_url", ""),
            "source_type": "SEC",
            "source_confidence": "secondary",
            "fetched_at": datetime.now().isoformat(),
        }
        results.append(record)

    # Save results
    if results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{_normalize_cik(cik)[1]}" if cik else ""
        out_path = RAW_DIR / f"fleet_disclosures{suffix}_{timestamp}.json"
        out_path.write_text(json.dumps(results, indent=2))
        print(f"Found {len(results)} fleet-related filing hits.")

    return results


def fetch_company_fleet_filings(cik: str, days: int = 90) -> list[dict]:
    """
    Fetch recent filings for a specific company and look for fleet
    disclosures in 10-Q/10-K filings.

    Args:
        cik: SEC CIK number
        days: Lookback window in days
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    cik_unpadded, cik_padded = _normalize_cik(cik)
    url = f"{EDGAR_SUBMISSIONS_BASE}/CIK{cik_padded}.json"

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    response = httpx.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Save raw submissions data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"submissions_{cik_padded}_{timestamp}.json"
    raw_path.write_text(json.dumps(data, indent=2))

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    filings: list[dict] = []
    for i in range(len(forms)):
        form_type = forms[i] if i < len(forms) else ""
        filing_date = dates[i] if i < len(dates) else ""

        if form_type not in ("10-Q", "10-K", "8-K"):
            continue
        if filing_date < cutoff:
            continue

        accession = (
            accessions[i].replace("-", "") if i < len(accessions) else ""
        )
        doc = primary_docs[i] if i < len(primary_docs) else ""
        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_unpadded}/{accession}/{doc}"
            if doc
            else ""
        )

        filings.append({
            "cik": cik_padded,
            "company_name": data.get("name", ""),
            "ticker": ",".join(data.get("tickers", [])),
            "form_type": form_type,
            "filing_date": filing_date,
            "filing_url": filing_url,
            "source_url": filing_url,
            "source_type": "SEC",
            "source_confidence": "secondary",
            "fetched_at": datetime.now().isoformat(),
        })

    print(
        f"Found {len(filings)} filings for "
        f"{data.get('name', cik_padded)} in last {days} days."
    )
    return filings


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch fleet deployment data from SEC EDGAR"
    )
    parser.add_argument("--cik", type=str, help="Company CIK number")
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Lookback window in days",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max EFTS search results",
    )
    args = parser.parse_args()

    if args.cik:
        print(f"--- Fetching filings for CIK {args.cik} ---")
        filings = fetch_company_fleet_filings(args.cik, days=args.days)
        print(f"Company filings: {len(filings)}")

    print(f"\n--- Searching EDGAR EFTS for fleet disclosures (last {args.days} days) ---")
    results = fetch_fleet_disclosures_efts(
        cik=args.cik, days=args.days, limit=args.limit
    )
    print(f"EFTS fleet hits: {len(results)}")
