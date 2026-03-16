"""
Patent Monitor -- Fetch Patents
Query the USPTO PatentsView API for quantum computing patents.
"""

import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path

RAW_DIR = Path("data/raw/quantum/patents")
PATENTSVIEW_API = "https://api.patentsview.org/patents/query"


def fetch_patents(
    assignee: str = "",
    days: int = 90,
    limit: int = 50,
) -> list[dict]:
    """
    Query USPTO PatentsView API for quantum computing patents.

    Args:
        assignee: Company/assignee name to filter (e.g. 'IBM', 'Google').
        days: Lookback window in days for grant date.
        limit: Maximum number of results.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Build query: quantum computing patents with optional assignee filter
    query_parts = [
        {"_or": [
            {"_text_any": {"patent_abstract": "quantum computing"}},
            {"_text_any": {"patent_abstract": "quantum processor"}},
            {"_text_any": {"patent_abstract": "qubit"}},
            {"_text_any": {"patent_title": "quantum"}},
        ]},
        {"_gte": {"patent_date": start_date}},
    ]

    if assignee:
        query_parts.append(
            {"_contains": {"assignee_organization": assignee}}
        )

    query = {"_and": query_parts}

    payload = {
        "q": json.dumps(query),
        "f": json.dumps([
            "patent_number",
            "patent_title",
            "patent_date",
            "patent_abstract",
            "assignee_organization",
            "assignee_country",
            "app_date",
        ]),
        "o": json.dumps({"per_page": limit, "page": 1}),
        "s": json.dumps([{"patent_date": "desc"}]),
    }

    try:
        response = httpx.get(PATENTSVIEW_API, params=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        print(f"PatentsView API request failed: {exc}")
        return []

    patents_raw = data.get("patents", [])
    results = []

    for patent in patents_raw:
        assignees = patent.get("assignees", [])
        assignee_name = assignees[0].get("assignee_organization", "") if assignees else ""

        record = {
            "patent_id": f"usp_{patent.get('patent_number', '')}",
            "patent_number": patent.get("patent_number", ""),
            "title": patent.get("patent_title", ""),
            "grant_date": patent.get("patent_date", ""),
            "filing_date": patent.get("applications", [{}])[0].get("app_date", "") if patent.get("applications") else "",
            "assignee": assignee_name,
            "country": assignees[0].get("assignee_country", "") if assignees else "",
            "abstract": (patent.get("patent_abstract", "") or "")[:500],
            "status": "granted",
            "source_url": f"https://patents.google.com/patent/US{patent.get('patent_number', '')}",
            "source_type": "USPTO",
            "source_confidence": "primary",
            "fetched_at": datetime.now().isoformat(),
        }
        results.append(record)

    return results


def run(assignee: str = "", days: int = 90, limit: int = 50) -> None:
    """Fetch patents and save to disk."""
    results = fetch_patents(assignee=assignee, days=days, limit=limit)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if results:
        suffix = f"_{assignee.replace(' ', '_').lower()}" if assignee else ""
        out_path = RAW_DIR / f"patents{suffix}_{timestamp}.json"
        out_path.write_text(json.dumps(results, indent=2))
        print(f"Saved {len(results)} patent records to {out_path}")
        for pat in results[:5]:
            print(f"  [{pat['grant_date']}] {pat['assignee']}: {pat['title'][:70]}")
        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more.")
    else:
        print("No patent records found matching criteria.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch quantum computing patents from USPTO")
    parser.add_argument("--assignee", type=str, default="", help="Company/assignee name filter")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of results")
    args = parser.parse_args()

    run(assignee=args.assignee, days=args.days, limit=args.limit)
