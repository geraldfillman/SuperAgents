"""
Partnership Tracker -- Fetch Partnerships
Search SEC EDGAR for 8-K filings mentioning autonomous vehicle
partnerships, OEM collaborations, and sensor supplier agreements.
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path("data/raw/autonomous_vehicles/partnerships")
EDGAR_EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"

USER_AGENT = os.getenv(
    "SEC_EDGAR_USER_AGENT",
    "AVRoboticsTracker research@example.com",
)


def _normalize_cik(cik: str) -> tuple[str, str]:
    """Return (unpadded, zero-padded-to-10) CIK."""
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    if not digits:
        raise ValueError("CIK must contain at least one digit")
    unpadded = digits.lstrip("0") or "0"
    padded = digits.zfill(10)
    return unpadded, padded


def search_partnership_filings(
    cik: str | None = None,
    days: int = 90,
    limit: int = 50,
) -> list[dict]:
    """
    Search EDGAR full-text for 8-K filings mentioning autonomous
    vehicle partnerships and collaborations.

    Args:
        cik: Optional CIK to restrict to a single company
        days: Lookback window in days
        limit: Max results
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT}
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    # Search for partnership/collaboration mentions in AV context
    query = (
        '("autonomous" OR "self-driving" OR "robotics") '
        'AND ("partnership" OR "collaboration" OR "joint venture" '
        'OR "strategic alliance" OR "supply agreement" '
        'OR "licensing agreement" OR "OEM agreement")'
    )

    params = {
        "q": query,
        "dateRange": "custom",
        "startdt": start_date,
        "enddt": end_date,
        "forms": "8-K",
    }

    response = httpx.get(
        EDGAR_EFTS_BASE, params=params, headers=headers, timeout=30
    )
    response.raise_for_status()
    data = response.json()

    hits = data.get("hits", {}).get("hits", [])[:limit]

    results: list[dict] = []
    for hit in hits:
        source = hit.get("_source", {})

        # If CIK filter specified, skip non-matching
        if cik:
            _, cik_padded = _normalize_cik(cik)
            entity_cik = str(source.get("entity_id", "")).zfill(10)
            if entity_cik != cik_padded:
                continue

        record = {
            "company_name": source.get("entity_name", ""),
            "cik": source.get("entity_id", ""),
            "filing_type": source.get("form_type", ""),
            "filing_date": source.get("file_date", ""),
            "filing_url": source.get("file_url", ""),
            "display_name": (
                source.get("display_names", [""])[0]
                if source.get("display_names")
                else ""
            ),
            "partnership_type": "UNKNOWN (requires filing parse)",
            "partner_name": "UNKNOWN (requires filing parse)",
            "source_url": source.get("file_url", ""),
            "source_type": "SEC",
            "source_confidence": "secondary",
            "fetched_at": datetime.now().isoformat(),
        }
        results.append(record)

    # Save results
    if results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{_normalize_cik(cik)[1]}" if cik else ""
        out_path = RAW_DIR / f"partnerships{suffix}_{timestamp}.json"
        out_path.write_text(json.dumps(results, indent=2))
        print(f"Found {len(results)} partnership-related 8-K filings.")

    return results


def classify_partnership_type(filing_text: str) -> str:
    """
    Classify the partnership type based on filing text content.

    Returns one of: OEM / fleet_operator / sensor_supplier / mapping / other
    """
    text_lower = filing_text.lower()

    oem_keywords = [
        "original equipment manufacturer", "oem", "vehicle manufacturer",
        "automaker", "vehicle platform",
    ]
    fleet_keywords = [
        "fleet operator", "ride-hail", "rideshare", "logistics partner",
        "delivery partner", "fleet management",
    ]
    sensor_keywords = [
        "lidar", "radar", "sensor", "perception", "camera system",
        "sensor suite", "sensor supplier",
    ]
    mapping_keywords = [
        "mapping", "hd map", "high-definition map", "geospatial",
        "localization",
    ]

    if any(kw in text_lower for kw in oem_keywords):
        return "OEM"
    if any(kw in text_lower for kw in fleet_keywords):
        return "fleet_operator"
    if any(kw in text_lower for kw in sensor_keywords):
        return "sensor_supplier"
    if any(kw in text_lower for kw in mapping_keywords):
        return "mapping"
    return "other"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Search SEC EDGAR for AV partnership filings"
    )
    parser.add_argument("--cik", type=str, help="Company CIK number")
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Lookback window in days",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max results",
    )
    args = parser.parse_args()

    results = search_partnership_filings(
        cik=args.cik, days=args.days, limit=args.limit
    )
    print(f"\nTotal partnership filings found: {len(results)}")
    for r in results[:10]:
        print(
            f"  [{r['filing_date']}] {r['company_name']} - "
            f"{r['filing_type']}"
        )
    if len(results) > 10:
        print(f"  ... and {len(results) - 10} more.")
