"""
PPA Monitor -- Fetch PPA Filings
Search SEC EDGAR EFTS for 8-K filings mentioning "power purchase agreement" or "PPA".
"""

import os
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path("data/raw/renewable_energy/ppa")
EFTS_BASE_URL = "https://efts.sec.gov/LATEST/search-index"
SUBMISSIONS_BASE = "https://data.sec.gov/submissions"

USER_AGENT = os.getenv(
    "SEC_EDGAR_USER_AGENT",
    "RenewableEnergyTracker research@example.com",
)

PPA_SEARCH_TERMS = [
    '"power purchase agreement"',
    '"PPA"',
    '"offtake agreement"',
    '"renewable energy certificate"',
]


def search_ppa_filings(
    cik: str | None = None,
    days: int = 30,
) -> list[dict]:
    """
    Search SEC EDGAR full-text for PPA-related 8-K filings.

    Args:
        cik: Optional CIK to restrict search to one company
        days: Lookback window in days
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    all_results: list[dict] = []

    for term in PPA_SEARCH_TERMS:
        params: dict = {
            "q": term,
            "dateRange": "custom",
            "startdt": start_date,
            "enddt": end_date,
            "forms": "8-K",
        }
        if cik:
            params["q"] = f"{term} AND cik:{cik}"

        try:
            response = httpx.get(
                EFTS_BASE_URL, params=params, headers=headers, timeout=30
            )
            response.raise_for_status()
            hits = response.json().get("hits", {}).get("hits", [])

            for hit in hits:
                source = hit.get("_source", {})
                filing_url = source.get("file_url", "")
                if not filing_url and source.get("file_num"):
                    filing_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&filenum={source['file_num']}"

                record = {
                    "company_name": source.get("display_names", [""])[0] if source.get("display_names") else "",
                    "cik": source.get("entity_id", ""),
                    "filing_date": source.get("file_date", ""),
                    "form_type": source.get("form_type", "8-K"),
                    "search_term": term,
                    "filing_url": filing_url,
                    "source_url": filing_url,
                    "source_type": "SEC",
                    "source_confidence": "secondary",
                    "extracted_at": datetime.now().isoformat(),
                }
                all_results.append(record)
        except httpx.HTTPError as exc:
            print(f"Error searching for {term}: {exc}")
            continue

    # Deduplicate by filing URL
    seen_urls: set[str] = set()
    unique_results: list[dict] = []
    for record in all_results:
        url = record.get("filing_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(record)

    # Save raw results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cik_tag = cik or "all"
    raw_path = RAW_DIR / f"ppa_filings_{cik_tag}_{timestamp}.json"
    raw_path.write_text(json.dumps(unique_results, indent=2))
    print(f"Saved {len(unique_results)} PPA-related filings to {raw_path}")

    return unique_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search SEC EDGAR for PPA-related 8-K filings"
    )
    parser.add_argument("--cik", type=str, help="Company CIK number")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days")
    args = parser.parse_args()

    results = search_ppa_filings(cik=args.cik, days=args.days)
    print(f"Found {len(results)} PPA-related filings in last {args.days} days")
    for r in results[:10]:
        print(f"  {r['filing_date']} | {r['company_name']} | {r['search_term']}")
