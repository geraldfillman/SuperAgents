"""
FDA Tracker — Fetch Drug Approvals
Queries the openFDA drug approvals endpoint and populates regulatory_events.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.biotech.io_utils import write_json
from super_agents.biotech.paths import DRUG_APPROVALS_RAW_DIR, ensure_biotech_directory
from super_agents.common.env import optional_env

load_dotenv()

OPENFDA_BASE = "https://api.fda.gov/drug/drugsfda.json"
# OpenFDA works unauthenticated but is rate-limited; key is genuinely optional.
API_KEY = optional_env("OPENFDA_API_KEY")
RAW_DIR = DRUG_APPROVALS_RAW_DIR


def fetch_recent_approvals(days: int = 30, limit: int = 100) -> list[dict]:
    """Fetch drug approvals from the last N days via openFDA."""
    ensure_biotech_directory(RAW_DIR)

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    params = {
        "search": f'submissions.submission_status_date:[{start_date}+TO+{end_date}]',
        "limit": limit,
    }
    if API_KEY:
        params["api_key"] = API_KEY

    response = httpx.get(OPENFDA_BASE, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Save raw response
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"approvals_{timestamp}.json"
    write_json(raw_path, data)

    results = data.get("results", [])
    return _transform_to_events(results)


def _transform_to_events(raw_results: list[dict]) -> list[dict]:
    """Transform openFDA results into regulatory_events format."""
    events = []
    for result in raw_results:
        sponsor = result.get("sponsor_name", "")
        products = result.get("products", [])
        submissions = result.get("submissions", [])

        for submission in submissions:
            if submission.get("submission_status") != "AP":
                continue  # Only approved

            for product in products:
                event = {
                    "product_name": product.get("brand_name", ""),
                    "generic_name": product.get("active_ingredients", [{}])[0].get("name", ""),
                    "sponsor": sponsor,
                    "event_type": "approval",
                    "event_date": submission.get("submission_status_date", ""),
                    "pathway": submission.get("submission_type", ""),  # NDA, BLA, etc.
                    "jurisdiction": "FDA",
                    "source_type": "FDA",
                    "source_confidence": "primary",
                    "official_fda_source_present": True,
                    "application_number": result.get("application_number", ""),
                }
                events.append(event)

    return events


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch recent FDA drug approvals")
    parser.add_argument("--days", type=int, default=30, help="Look back N days (1–365)")
    parser.add_argument("--limit", type=int, default=100, help="Max results (1–1000)")
    args = parser.parse_args()

    if not (1 <= args.days <= 365):
        parser.error("--days must be between 1 and 365")
    if not (1 <= args.limit <= 1000):
        parser.error("--limit must be between 1 and 1000")

    approvals = fetch_recent_approvals(days=args.days, limit=args.limit)
    print(f"Found {len(approvals)} approval events")
    for event in approvals[:5]:
        print(f"  {event['event_date']} | {event['product_name']} | {event['pathway']}")
