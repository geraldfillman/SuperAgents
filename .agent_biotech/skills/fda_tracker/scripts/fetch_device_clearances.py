"""
FDA Tracker — Fetch Device Clearances
Queries FDA 510(k), PMA, and De Novo databases for device clearances and approvals.
"""

import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

RAW_DIR = Path("data/raw/fda/device_clearances")

# openFDA device endpoints
DEVICE_510K_URL = "https://api.fda.gov/device/510k.json"
DEVICE_PMA_URL = "https://api.fda.gov/device/pma.json"


def fetch_510k_clearances(days: int = 30, limit: int = 100) -> list[dict]:
    """Fetch recent 510(k) clearances via openFDA device API."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    params = {
        "search": f"decision_date:[{start_date}+TO+{end_date}]",
        "limit": limit,
    }

    response = httpx.get(DEVICE_510K_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"510k_{timestamp}.json"
    raw_path.write_text(json.dumps(data, indent=2))

    return _transform_510k(data.get("results", []))


def fetch_pma_approvals(days: int = 30, limit: int = 100) -> list[dict]:
    """Fetch recent PMA approvals via openFDA device API."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    params = {
        "search": f"decision_date:[{start_date}+TO+{end_date}]",
        "limit": limit,
    }

    response = httpx.get(DEVICE_PMA_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"pma_{timestamp}.json"
    raw_path.write_text(json.dumps(data, indent=2))

    return _transform_pma(data.get("results", []))


def _transform_510k(results: list[dict]) -> list[dict]:
    """Transform 510(k) results into regulatory_events format."""
    events = []
    for r in results:
        events.append({
            "device_name": r.get("device_name", ""),
            "applicant": r.get("applicant", ""),
            "event_type": "510k_clearance",
            "event_date": r.get("decision_date", ""),
            "pathway": "510(k)",
            "k_number": r.get("k_number", ""),
            "product_code": r.get("product_code", ""),
            "decision_description": r.get("decision_description", ""),
            "jurisdiction": "FDA",
            "source_type": "FDA",
            "source_confidence": "primary",
            "official_fda_source_present": True,
        })
    return events


def _transform_pma(results: list[dict]) -> list[dict]:
    """Transform PMA results into regulatory_events format."""
    events = []
    for r in results:
        events.append({
            "device_name": r.get("trade_name", ""),
            "applicant": r.get("applicant", ""),
            "event_type": "pma_approval",
            "event_date": r.get("decision_date", ""),
            "pathway": "PMA",
            "pma_number": r.get("pma_number", ""),
            "product_code": r.get("product_code", ""),
            "jurisdiction": "FDA",
            "source_type": "FDA",
            "source_confidence": "primary",
            "official_fda_source_present": True,
        })
    return events


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch FDA device clearances/approvals")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--pathway", choices=["510k", "pma", "all"], default="all")
    args = parser.parse_args()

    if args.pathway in ("510k", "all"):
        clearances = fetch_510k_clearances(days=args.days, limit=args.limit)
        print(f"510(k): {len(clearances)} clearances")
        for c in clearances[:3]:
            print(f"  {c['event_date']} | {c['device_name']} | {c['applicant']}")

    if args.pathway in ("pma", "all"):
        approvals = fetch_pma_approvals(days=args.days, limit=args.limit)
        print(f"PMA: {len(approvals)} approvals")
        for a in approvals[:3]:
            print(f"  {a['event_date']} | {a['device_name']} | {a['applicant']}")
