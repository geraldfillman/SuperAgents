"""
DPA Award Tracker -- Fetch Defense Production Act Awards
Query USAspending.gov API for DPA Title III awards related to critical
minerals and rare earth elements.
"""

import os
import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Constants
BASE_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
RAW_DIR = Path("data/raw/rare_earth/dpa_awards")

# Keywords for critical minerals DPA awards
CRITICAL_MINERAL_KEYWORDS = [
    "critical minerals",
    "rare earth",
    "lithium",
    "cobalt",
    "nickel",
    "graphite",
    "manganese",
    "tungsten",
    "titanium",
    "vanadium",
    "gallium",
    "germanium",
    "indium",
    "Defense Production Act",
    "DPA Title III",
]

# Relevant agency codes
DPA_AGENCY_CODES = [
    "9700",  # Department of Defense
    "8900",  # Department of Energy
    "1400",  # Department of the Interior
]


def fetch_dpa_awards(days: int = 365, limit: int = 100) -> list[dict]:
    """
    Fetch DPA Title III awards for critical minerals from USAspending.gov.

    Args:
        days: Number of days to look back for awards.
        limit: Maximum number of results to return.

    Returns:
        List of DPA award records with source metadata.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    all_results = []

    for keyword in CRITICAL_MINERAL_KEYWORDS:
        payload = {
            "filters": {
                "keyword": keyword,
                "time_period": [
                    {
                        "start_date": start_date,
                        "end_date": end_date,
                    }
                ],
                "award_type_codes": ["A", "B", "C", "D"],  # Contracts
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
                "Contract Award Type",
            ],
            "limit": min(limit, 50),
            "page": 1,
            "sort": "Award Amount",
            "order": "desc",
        }

        try:
            response = httpx.post(
                BASE_URL,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            all_results.extend(results)
        except httpx.HTTPError as exc:
            print(f"Error fetching keyword '{keyword}': {exc}")
            continue

        if len(all_results) >= limit:
            break

    # Deduplicate by Award ID
    seen = set()
    unique = []
    for award in all_results:
        award_id = award.get("Award ID", "")
        if award_id and award_id not in seen:
            seen.add(award_id)
            unique.append(award)

    unique = unique[:limit]

    # Save raw
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"usaspending_{timestamp}.json"
    raw_path.write_text(json.dumps(unique, indent=2))

    # Transform
    transformed = _transform(unique)

    processed_path = RAW_DIR / f"dpa_awards_processed_{timestamp}.json"
    processed_path.write_text(json.dumps(transformed, indent=2))

    return transformed


def _transform(raw: list[dict]) -> list[dict]:
    """Transform raw USAspending results to standard schema format."""
    records = []
    for award in raw:
        program = _classify_program(
            award.get("Description", ""),
            award.get("Awarding Agency", ""),
        )

        award_id = award.get("Award ID", "")
        usa_spending_url = (
            f"https://www.usaspending.gov/award/{award_id}"
            if award_id else ""
        )

        records.append({
            "award_id": award_id,
            "recipient_name": award.get("Recipient Name", ""),
            "award_amount_usd": award.get("Award Amount", 0),
            "description": award.get("Description", ""),
            "start_date": award.get("Start Date", ""),
            "end_date": award.get("End Date", ""),
            "awarding_agency": award.get("Awarding Agency", ""),
            "awarding_sub_agency": award.get("Awarding Sub Agency", ""),
            "program": program,
            "source_url": usa_spending_url,
            "source_type": "USAspending",
            "source_confidence": "primary",
            "fetched_at": datetime.now().isoformat(),
        })
    return records


def _classify_program(description: str, agency: str) -> str:
    """Classify the DPA program type."""
    text = (description + " " + agency).lower()
    if "title iii" in text or "dpa" in text or "defense production" in text:
        return "Title_III"
    if "cmmc" in text:
        return "CMMC"
    if "defense" in text:
        return "DPA"
    return "other"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch DPA Title III critical minerals awards from USAspending.gov"
    )
    parser.add_argument("--days", type=int, default=365, help="Lookback window in days")
    parser.add_argument("--limit", type=int, default=100, help="Maximum results")
    args = parser.parse_args()

    results = fetch_dpa_awards(days=args.days, limit=args.limit)
    print(f"Found {len(results)} DPA awards")
    for r in results[:5]:
        print(
            f"  [{r['start_date']}] ${r['award_amount_usd']:,.0f}"
            f" - {r['recipient_name']} ({r['program']})"
        )
