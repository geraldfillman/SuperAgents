"""
IRA Credit Tracker -- Fetch IRA Credits
Query DOE/IRS data on IRA clean energy credits via the Federal Register API.
"""

import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import httpx

RAW_DIR = Path("data/raw/renewable_energy/ira_credits")
FEDERAL_REGISTER_API = "https://www.federalregister.gov/api/v1/documents.json"

IRA_SEARCH_TERMS = [
    "investment tax credit",
    "production tax credit",
    "clean energy",
    "45X manufacturing",
    "45V clean hydrogen",
    "48C advanced energy",
    "IRA tax credit",
    "Inflation Reduction Act",
]


def fetch_ira_credit_documents(
    days: int = 30,
    limit: int = 50,
) -> list[dict]:
    """
    Query the Federal Register API for IRA clean energy credit documents.

    Args:
        days: Lookback window in days
        limit: Maximum results per search term
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    all_results: list[dict] = []
    seen_urls: set[str] = set()

    for term in IRA_SEARCH_TERMS:
        params = {
            "conditions[term]": term,
            "conditions[agencies][]": "internal-revenue-service",
            "conditions[publication_date][gte]": start_date,
            "per_page": limit,
            "order": "newest",
        }

        try:
            response = httpx.get(
                FEDERAL_REGISTER_API, params=params, timeout=30
            )
            response.raise_for_status()
            data = response.json()

            for doc in data.get("results", []):
                doc_url = doc.get("html_url", "")
                if doc_url in seen_urls:
                    continue
                seen_urls.add(doc_url)

                # Determine credit type from document content
                credit_type = _classify_credit_type(
                    doc.get("title", ""), doc.get("abstract", "")
                )

                record = {
                    "document_number": doc.get("document_number", ""),
                    "title": doc.get("title", ""),
                    "abstract": doc.get("abstract", ""),
                    "publication_date": doc.get("publication_date", ""),
                    "document_type": doc.get("type", ""),
                    "agencies": [
                        a.get("name", "") for a in doc.get("agencies", [])
                    ],
                    "credit_type": credit_type,
                    "search_term": term,
                    "source_url": doc_url,
                    "source_type": "Federal_Register",
                    "source_confidence": "primary",
                    "extracted_at": datetime.now().isoformat(),
                }
                all_results.append(record)
        except httpx.HTTPError as exc:
            print(f"Error searching Federal Register for '{term}': {exc}")
            continue

    # Save raw results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"ira_credits_{timestamp}.json"
    raw_path.write_text(json.dumps(all_results, indent=2))
    print(f"Saved {len(all_results)} IRA credit documents to {raw_path}")

    return all_results


def _classify_credit_type(title: str, abstract: str) -> str:
    """Classify the IRA credit type based on document title and abstract."""
    combined = (title + " " + (abstract or "")).lower()

    if "45x" in combined or "manufacturing" in combined:
        return "45X"
    if "45v" in combined or "hydrogen" in combined:
        return "45V"
    if "48c" in combined or "advanced energy" in combined:
        return "48C"
    if "production tax credit" in combined or "ptc" in combined:
        return "PTC"
    if "investment tax credit" in combined or "itc" in combined:
        return "ITC"
    return "UNKNOWN"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch IRA clean energy credit documents from Federal Register"
    )
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days")
    parser.add_argument("--limit", type=int, default=50, help="Max results per term")
    args = parser.parse_args()

    results = fetch_ira_credit_documents(days=args.days, limit=args.limit)
    print(f"Found {len(results)} IRA credit documents in last {args.days} days")
    for r in results[:10]:
        print(f"  {r['publication_date']} | {r['credit_type']} | {r['title'][:80]}")
