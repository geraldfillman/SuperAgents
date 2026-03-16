"""
FDA Tracker — Fetch Postmarketing Requirements
Pulls postmarketing requirements and commitments from FDA databases.
"""

import json
import httpx
from datetime import datetime
from pathlib import Path

RAW_DIR = Path("data/raw/fda/postmarketing")

# openFDA doesn't have a direct PMR endpoint, so we use the FDA PMR/PMC page
PMR_SEARCH_URL = "https://www.accessdata.fda.gov/scripts/cder/pmc/index.cfm"


def fetch_postmarketing_requirements(application_number: str | None = None) -> list[dict]:
    """
    Fetch postmarketing requirements/commitments.
    If application_number is provided, searches for that specific application.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # For now, use the openFDA drug endpoint to find PMR-related info
    # The FDA PMR database requires form-based searching
    params = {}
    if application_number:
        params["search"] = f"application_number:{application_number}"
        params["limit"] = 10

    # TODO: Implement full PMR database scraping
    # The FDA PMR/PMC database at accessdata.fda.gov requires POST-based form submission
    # For MVP, extract PMR info from drug approval records

    return []


def extract_pmr_from_approval(approval_data: dict) -> list[dict]:
    """Extract postmarketing requirement references from approval data."""
    pmr_records = []

    submissions = approval_data.get("submissions", [])
    for sub in submissions:
        # Look for accelerated approval or conditional markers
        review_priority = sub.get("review_priority", "")
        submission_type = sub.get("submission_type", "")

        if review_priority in ("PRIORITY", "STANDARD"):
            pmr_records.append({
                "application_number": approval_data.get("application_number", ""),
                "approval_context": "accelerated" if "accelerated" in str(sub).lower() else "standard",
                "commitment_type": "PMR",  # Default; refine with actual PMR data
                "requirement_summary": "Postmarketing study may be required — verify against PMR database",
                "status": "pending",
                "source_type": "FDA",
                "source_confidence": "secondary",  # Inferred, not directly from PMR DB
                "fetched_at": datetime.now().isoformat(),
            })

    return pmr_records


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch FDA postmarketing requirements")
    parser.add_argument("--application", type=str, help="Application number (e.g., NDA012345)")
    args = parser.parse_args()

    records = fetch_postmarketing_requirements(application_number=args.application)
    print(f"Found {len(records)} postmarketing records")
