"""
SBIR Tracker -- Fetch SBIR Awards
Query USAspending.gov API for SBIR/STTR awards related to quantum computing.
"""

import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path

RAW_DIR = Path("data/raw/quantum/sbir")
USASPENDING_API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


def fetch_sbir_awards(days: int = 90, limit: int = 50) -> list[dict]:
    """
    Query USAspending.gov for SBIR/STTR awards related to quantum computing.

    Args:
        days: Lookback window in days for award action date.
        limit: Maximum number of results.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    payload = {
        "filters": {
            "keywords": ["quantum computing", "quantum processor", "qubit", "quantum error correction"],
            "time_period": [
                {
                    "start_date": start_date,
                    "end_date": end_date,
                }
            ],
            "award_type_codes": ["A", "B", "C", "D"],
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Description",
            "Start Date",
            "End Date",
            "Awarding Agency",
            "Awarding Sub Agency",
            "generated_internal_id",
        ],
        "limit": limit,
        "page": 1,
        "sort": "Award Amount",
        "order": "desc",
    }

    try:
        response = httpx.post(USASPENDING_API, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        print(f"USAspending API request failed: {exc}")
        return []

    awards_raw = data.get("results", [])
    results = []

    for award in awards_raw:
        internal_id = award.get("generated_internal_id", "")
        record = {
            "award_id": f"usa_{internal_id}" if internal_id else f"usa_{award.get('Award ID', '')}",
            "award_number": award.get("Award ID", ""),
            "recipient_name": award.get("Recipient Name", ""),
            "award_amount_usd": award.get("Award Amount", 0.0),
            "description": (award.get("Description", "") or "")[:500],
            "start_date": award.get("Start Date", ""),
            "end_date": award.get("End Date", ""),
            "agency": award.get("Awarding Agency", ""),
            "sub_agency": award.get("Awarding Sub Agency", ""),
            "program": "SBIR/STTR",
            "source_url": f"https://www.usaspending.gov/award/{internal_id}" if internal_id else "",
            "source_type": "USAspending",
            "source_confidence": "primary",
            "fetched_at": datetime.now().isoformat(),
        }
        results.append(record)

    return results


def run(days: int = 90, limit: int = 50) -> None:
    """Fetch SBIR/STTR awards and save to disk."""
    results = fetch_sbir_awards(days=days, limit=limit)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if results:
        out_path = RAW_DIR / f"sbir_awards_{timestamp}.json"
        out_path.write_text(json.dumps(results, indent=2))
        print(f"Saved {len(results)} SBIR/STTR award records to {out_path}")
        total_funding = sum(r.get("award_amount_usd", 0) for r in results)
        print(f"  Total funding: ${total_funding:,.0f}")
        for r in results[:5]:
            print(f"  [{r['agency']}] {r['recipient_name']}: ${r['award_amount_usd']:,.0f}")
        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more.")
    else:
        print("No SBIR/STTR awards found matching quantum criteria.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch quantum SBIR/STTR awards from USAspending.gov")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of results")
    args = parser.parse_args()

    run(days=args.days, limit=args.limit)
