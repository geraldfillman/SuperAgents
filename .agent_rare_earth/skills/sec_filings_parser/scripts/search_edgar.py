"""
SEC Filings Parser -- Search EDGAR
Search SEC EDGAR for company filings by CIK, ticker, or filing type.
Adapted for rare earth and critical minerals companies.
"""

import os
import json
import httpx
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path("data/raw/rare_earth/sec")
EDGAR_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
EDGAR_SEARCH_BASE = "https://efts.sec.gov/LATEST/search-index"

USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "RareEarthTracker research@example.com")


from super_agents.common.cik import normalize_cik  # noqa: E402 -- centralized CIK util


def get_company_filings(cik: str, filing_types: list[str] | None = None) -> list[dict]:
    """
    Fetch recent filings for a company by CIK number.

    Args:
        cik: SEC CIK number (will be zero-padded to 10 digits)
        filing_types: Filter by type, e.g. ["8-K", "10-Q", "10-K"]
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    cik_unpadded, cik_padded = normalize_cik(cik)
    url = f"{EDGAR_SUBMISSIONS_BASE}/CIK{cik_padded}.json"

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    response = httpx.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Save raw
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"filings_{cik_padded}_{timestamp}.json"
    raw_path.write_text(json.dumps(data, indent=2))

    # Extract recent filings
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    filings = []
    for i in range(len(forms)):
        form_type = forms[i] if i < len(forms) else ""
        if filing_types and form_type not in filing_types:
            continue

        accession = accessions[i].replace("-", "") if i < len(accessions) else ""
        filing = {
            "cik": cik_padded,
            "company_name": data.get("name", ""),
            "ticker": ",".join(data.get("tickers", [])),
            "form_type": form_type,
            "filing_date": dates[i] if i < len(dates) else "",
            "accession_number": accessions[i] if i < len(accessions) else "",
            "primary_document": primary_docs[i] if i < len(primary_docs) else "",
            "filing_url": (
                f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession}/"
                f"{primary_docs[i]}" if i < len(primary_docs) else ""
            ),
            "source_type": "SEC",
            "source_confidence": "secondary",
        }
        filings.append(filing)

    return filings


def search_full_text(query: str, filing_type: str | None = None, date_range: str | None = None) -> list[dict]:
    """
    Full-text search across EDGAR filings.

    Args:
        query: Search terms (e.g., "NI 43-101", "offtake agreement", "resource estimate")
        filing_type: Filter by form type
        date_range: Date range filter
    """
    headers = {"User-Agent": USER_AGENT}
    params = {"q": query, "dateRange": "custom", "startdt": "", "enddt": ""}

    if filing_type:
        params["forms"] = filing_type

    response = httpx.get(EDGAR_SEARCH_BASE, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get("hits", {}).get("hits", [])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Search SEC EDGAR filings")
    parser.add_argument("--cik", type=str, help="Company CIK number")
    parser.add_argument("--types", nargs="+", default=["8-K", "10-Q", "10-K"],
                        help="Filing types to include")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.cik:
        filings = get_company_filings(args.cik, filing_types=args.types)
        print(f"Found {len(filings)} filings for CIK {args.cik}")
        for f in filings[:args.limit]:
            print(f"  {f['filing_date']} | {f['form_type']} | {f['company_name']}")
