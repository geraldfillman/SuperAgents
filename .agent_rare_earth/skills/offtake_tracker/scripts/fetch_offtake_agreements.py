"""
Offtake Tracker -- Fetch Offtake Agreements from SEC EDGAR
Search SEC EDGAR for 8-K filings mentioning offtake agreements
for mining and critical minerals companies.
"""

import os
import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Constants
EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions"
RAW_DIR = Path("data/raw/rare_earth/offtake")

USER_AGENT = os.getenv(
    "SEC_EDGAR_USER_AGENT",
    "RareEarthTracker research@example.com",
)

OFFTAKE_SEARCH_TERMS = [
    '"offtake agreement" mining',
    '"offtake agreement" lithium',
    '"offtake agreement" rare earth',
    '"offtake agreement" critical minerals',
    '"supply agreement" mineral',
    '"binding offtake"',
    '"non-binding offtake"',
]


def fetch_offtake_agreements(cik: str | None = None, days: int = 90) -> list[dict]:
    """
    Search SEC EDGAR 8-K filings for offtake agreement announcements.

    Args:
        cik: Optional CIK to filter by company.
        days: Lookback window in days.

    Returns:
        List of offtake agreement records with source metadata.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    all_results = []

    for term in OFFTAKE_SEARCH_TERMS:
        params = {
            "q": term,
            "forms": "8-K",
            "dateRange": "custom",
            "startdt": start_date,
            "enddt": end_date,
        }

        if cik:
            params["ciks"] = cik

        try:
            response = httpx.get(
                EDGAR_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            hits = data.get("hits", {}).get("hits", [])
            all_results.extend(hits)
        except httpx.HTTPError as exc:
            print(f"Error searching for '{term}': {exc}")
            continue

    # Deduplicate by accession number
    seen = set()
    unique = []
    for hit in all_results:
        source = hit.get("_source", {})
        accession = source.get("accession_no", "")
        if accession and accession not in seen:
            seen.add(accession)
            unique.append(hit)

    # Save raw
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"offtake_search_{timestamp}.json"
    raw_path.write_text(json.dumps(unique, indent=2))

    # Transform
    transformed = _transform(unique)

    processed_path = RAW_DIR / f"offtake_processed_{timestamp}.json"
    processed_path.write_text(json.dumps(transformed, indent=2))

    return transformed


def _transform(raw: list[dict]) -> list[dict]:
    """Transform raw EDGAR search results to standard schema format."""
    records = []
    for hit in raw:
        source = hit.get("_source", {})

        accession = source.get("accession_no", "")
        entity_id = source.get("entity_id", "")
        filing_url = ""
        if accession and entity_id:
            clean_accession = accession.replace("-", "")
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{entity_id}/{clean_accession}"
            )

        records.append({
            "accession_number": accession,
            "entity_name": source.get("entity_name", ""),
            "entity_id": entity_id,
            "form_type": source.get("form_type", ""),
            "filing_date": source.get("file_date", ""),
            "description": source.get("file_description", ""),
            "agreement_type": _classify_agreement_type(
                str(source.get("file_description", ""))
            ),
            "source_url": filing_url,
            "source_type": "SEC",
            "source_confidence": "secondary",
            "fetched_at": datetime.now().isoformat(),
        })
    return records


def _classify_agreement_type(description: str) -> str:
    """Classify the type of offtake agreement."""
    text = description.lower()
    if "binding" in text and "non-binding" not in text:
        return "binding"
    if "non-binding" in text:
        return "non-binding"
    if "supply" in text:
        return "supply_agreement"
    if "letter of intent" in text or "loi" in text:
        return "LOI"
    return "offtake"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Search SEC EDGAR for mining offtake agreements"
    )
    parser.add_argument("--cik", type=str, default=None, help="Company CIK number")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days")
    args = parser.parse_args()

    results = fetch_offtake_agreements(cik=args.cik, days=args.days)
    print(f"Found {len(results)} offtake-related filings")
    for r in results[:5]:
        print(
            f"  [{r['filing_date']}] {r['agreement_type']} - {r['entity_name']}"
        )
