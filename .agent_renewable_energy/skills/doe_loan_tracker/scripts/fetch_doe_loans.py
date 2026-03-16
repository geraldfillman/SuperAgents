"""
DOE Loan Tracker -- Fetch DOE Loans
Query USAspending.gov for DOE Loan Programs Office awards.
"""

import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import httpx

RAW_DIR = Path("data/raw/renewable_energy/doe_loans")
USASPENDING_API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# DOE agency codes
DOE_AGENCY_CODE = "089"  # Department of Energy
# LPO sub-tier codes
LPO_SUBTIER_CODES = ["8900", "8959"]


def fetch_doe_loan_awards(
    days: int = 90,
    limit: int = 50,
) -> list[dict]:
    """
    Query USAspending.gov for DOE Loan Programs Office awards.

    Args:
        days: Lookback window in days
        limit: Maximum results to return
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    payload = {
        "filters": {
            "agencies": [
                {
                    "type": "funding",
                    "tier": "toptier",
                    "name": "Department of Energy",
                }
            ],
            "award_type_codes": ["07", "08"],  # Direct loans, guaranteed loans
            "time_period": [
                {"start_date": start_date, "end_date": end_date}
            ],
            "keywords": [
                "loan programs office",
                "LPO",
                "ATVM",
                "Title XVII",
                "clean energy",
                "renewable",
                "battery",
            ],
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
            "Award Type",
        ],
        "limit": limit,
        "page": 1,
        "sort": "Award Amount",
        "order": "desc",
    }

    headers = {"Content-Type": "application/json"}

    response = httpx.post(
        USASPENDING_API, json=payload, headers=headers, timeout=30
    )
    response.raise_for_status()
    data = response.json()

    results = []
    for award in data.get("results", []):
        program = _classify_program(
            award.get("Description", ""),
            award.get("Awarding Sub Agency", ""),
        )

        record = {
            "award_id": award.get("Award ID", ""),
            "recipient_name": award.get("Recipient Name", ""),
            "amount_usd": award.get("Award Amount"),
            "description": award.get("Description", ""),
            "start_date": award.get("Start Date", ""),
            "end_date": award.get("End Date", ""),
            "awarding_agency": award.get("Awarding Agency", ""),
            "awarding_sub_agency": award.get("Awarding Sub Agency", ""),
            "award_type": award.get("Award Type", ""),
            "program": program,
            "source_url": f"https://www.usaspending.gov/award/{award.get('Award ID', '')}",
            "source_type": "USAspending",
            "source_confidence": "primary",
            "extracted_at": datetime.now().isoformat(),
        }
        results.append(record)

    # Save raw results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"doe_loans_{timestamp}.json"
    raw_path.write_text(json.dumps(results, indent=2))
    print(f"Saved {len(results)} DOE loan awards to {raw_path}")

    return results


def _classify_program(description: str, sub_agency: str) -> str:
    """Classify the DOE loan program based on description."""
    combined = (description + " " + sub_agency).lower()

    if "atvm" in combined or "advanced technology vehicle" in combined:
        return "ATVM"
    if "title xvii" in combined or "title 17" in combined:
        return "Title_XVII"
    if "loan programs office" in combined or "lpo" in combined:
        return "LPO"
    return "LPO"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch DOE Loan Programs Office awards from USAspending.gov"
    )
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days")
    parser.add_argument("--limit", type=int, default=50, help="Max results to return")
    args = parser.parse_args()

    results = fetch_doe_loan_awards(days=args.days, limit=args.limit)
    print(f"Found {len(results)} DOE loan awards in last {args.days} days")
    for r in results[:10]:
        print(
            f"  {r['start_date']} | {r['program']} | {r['recipient_name']} | "
            f"${r['amount_usd']:,.0f}" if r['amount_usd'] else
            f"  {r['start_date']} | {r['program']} | {r['recipient_name']}"
        )
