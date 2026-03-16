"""
Enforcement Monitor -- Fetch Enforcement Actions
Query the CFPB enforcement database and check Federal Register for
FinCEN actions against fintech companies.
"""

import json
import os
import sys
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.fintech.io_utils import write_json
from super_agents.fintech.paths import ENFORCEMENT_RAW_DIR, ensure_fintech_directory

load_dotenv()

CFPB_ENFORCEMENT_BASE = "https://www.consumerfinance.gov/data-research/enforcement/api"
FEDERAL_REGISTER_BASE = "https://www.federalregister.gov/api/v1/documents.json"
RAW_DIR = ENFORCEMENT_RAW_DIR

USER_AGENT = os.getenv("FINTECH_USER_AGENT", "FintechTracker research@example.com")


def fetch_cfpb_enforcement(days: int = 90, limit: int = 100) -> list[dict]:
    """
    Query the CFPB enforcement actions API for recent actions.

    Args:
        days: Look back N days
        limit: Maximum results to return
    """
    ensure_fintech_directory(RAW_DIR)

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    params = {
        "date_filed_min": start_date,
        "date_filed_max": end_date,
        "size": limit,
    }
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    response = httpx.get(CFPB_ENFORCEMENT_BASE, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Save raw response
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"cfpb_enforcement_{timestamp}.json"
    write_json(raw_path, data)

    results = data.get("results", data) if isinstance(data, dict) else data
    if not isinstance(results, list):
        results = [results] if results else []

    return _transform_cfpb_results(results)


def _transform_cfpb_results(raw_results: list[dict]) -> list[dict]:
    """Transform CFPB enforcement results into enforcement_actions format."""
    actions = []
    for result in raw_results:
        defendants = result.get("defendant", result.get("defendants", []))
        if isinstance(defendants, str):
            defendants = [defendants]

        for defendant in defendants:
            defendant_name = defendant if isinstance(defendant, str) else defendant.get("name", "")
            action = {
                "company_name": defendant_name,
                "agency": "CFPB",
                "action_type": result.get("action_type", result.get("type", "")),
                "action_date": result.get("date_filed", result.get("initial_filing_date", "")),
                "penalty_usd": _extract_penalty(result),
                "description": result.get("relief_summary", result.get("description", ""))[:500],
                "docket_number": result.get("docket_number", ""),
                "source_url": result.get("url", f"https://www.consumerfinance.gov/enforcement/actions/"),
                "source_type": "CFPB",
                "source_confidence": "primary",
            }
            actions.append(action)

    return actions


def _extract_penalty(result: dict) -> float:
    """Extract penalty amount from enforcement result."""
    for field in ("civil_money_penalty", "penalty", "amount", "relief_amount"):
        value = result.get(field)
        if value is not None:
            try:
                return float(str(value).replace(",", "").replace("$", ""))
            except ValueError:
                continue
    return 0.0


def fetch_fincen_actions(days: int = 90, limit: int = 50) -> list[dict]:
    """
    Check Federal Register for FinCEN enforcement actions.

    Args:
        days: Look back N days
        limit: Maximum results to return
    """
    ensure_fintech_directory(RAW_DIR)

    end_date = datetime.now().strftime("%m/%d/%Y")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%m/%d/%Y")

    params = {
        "conditions[agencies][]": "financial-crimes-enforcement-network",
        "conditions[type][]": "NOTICE",
        "conditions[publication_date][gte]": start_date,
        "conditions[publication_date][lte]": end_date,
        "per_page": limit,
        "order": "newest",
    }
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    response = httpx.get(FEDERAL_REGISTER_BASE, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Save raw response
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"fincen_actions_{timestamp}.json"
    write_json(raw_path, data)

    results = data.get("results", [])
    actions = []
    for result in results:
        title = result.get("title", "")
        # Filter for enforcement-related notices
        enforcement_terms = ["assessment", "penalty", "enforcement", "violation", "consent"]
        if not any(term in title.lower() for term in enforcement_terms):
            continue

        action = {
            "company_name": title,  # FinCEN titles typically contain entity name
            "agency": "FinCEN",
            "action_type": result.get("type", "notice"),
            "action_date": result.get("publication_date", ""),
            "penalty_usd": 0.0,  # Requires deeper parsing of the document
            "description": result.get("abstract", "")[:500],
            "document_number": result.get("document_number", ""),
            "source_url": result.get("html_url", result.get("url", "")),
            "source_type": "Federal Register",
            "source_confidence": "primary",
        }
        actions.append(action)

    return actions


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch enforcement actions against fintech companies")
    parser.add_argument("--days", type=int, default=90, help="Look back N days")
    parser.add_argument("--limit", type=int, default=100, help="Max results")
    args = parser.parse_args()

    print(f"Fetching CFPB enforcement actions (last {args.days} days)...")
    cfpb_actions = fetch_cfpb_enforcement(days=args.days, limit=args.limit)
    print(f"Found {len(cfpb_actions)} CFPB enforcement actions")
    for a in cfpb_actions[:5]:
        print(f"  {a['action_date']} | {a['company_name'][:40]} | ${a['penalty_usd']:,.0f}")

    print(f"\nFetching FinCEN actions (last {args.days} days)...")
    fincen_actions = fetch_fincen_actions(days=args.days, limit=args.limit)
    print(f"Found {len(fincen_actions)} FinCEN enforcement actions")
    for a in fincen_actions[:5]:
        print(f"  {a['action_date']} | {a['company_name'][:60]}")
