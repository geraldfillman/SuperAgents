"""
Permit Tracker -- Fetch AV Permits
Query California DMV AV testing reports, NHTSA SGO crash reports,
and SEC EDGAR for NHTSA exemption petitions.
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path("data/raw/autonomous_vehicles/permits")
EDGAR_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
EDGAR_EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"
NHTSA_API_BASE = "https://api.nhtsa.gov"

USER_AGENT = os.getenv(
    "SEC_EDGAR_USER_AGENT",
    "AVRoboticsTracker research@example.com",
)

# California DMV publishes AV testing permit holders and annual
# disengagement reports at this public URL.
CA_DMV_PERMITS_URL = (
    "https://www.dmv.ca.gov/portal/vehicle-industry-services/"
    "autonomous-vehicles/autonomous-vehicle-testing-permit-holders/"
)


def fetch_ca_dmv_permit_list() -> list[dict]:
    """
    Fetch the California DMV autonomous vehicle testing permit holder
    page and extract structured permit records.

    The CA DMV does not expose a JSON API; the data is published as
    HTML tables. We fetch the page and parse the table rows.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT}
    response = httpx.get(CA_DMV_PERMITS_URL, headers=headers, timeout=30)
    response.raise_for_status()

    # Save raw HTML for auditing
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"ca_dmv_permits_{timestamp}.html"
    raw_path.write_text(response.text, encoding="utf-8")

    # Parse the HTML table (requires beautifulsoup4)
    permits: list[dict] = []
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.text, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            headers_row = rows[0] if rows else None
            if headers_row is None:
                continue
            col_names = [
                th.get_text(strip=True).lower().replace(" ", "_")
                for th in headers_row.find_all(["th", "td"])
            ]
            for row in rows[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) != len(col_names):
                    continue
                record = dict(zip(col_names, cells))
                record["source_url"] = CA_DMV_PERMITS_URL
                record["source_type"] = "CA_DMV"
                record["source_confidence"] = "primary"
                record["fetched_at"] = datetime.now().isoformat()
                permits.append(record)
    except ImportError:
        print(
            "WARNING: beautifulsoup4 not installed. "
            "Raw HTML saved but not parsed."
        )

    # Save structured permits
    if permits:
        out_path = RAW_DIR / f"ca_dmv_permits_{timestamp}.json"
        out_path.write_text(json.dumps(permits, indent=2))
        print(f"Fetched {len(permits)} CA DMV permit records.")

    return permits


def fetch_nhtsa_exemption_petitions_via_edgar(
    days: int = 30,
    limit: int = 50,
) -> list[dict]:
    """
    Search SEC EDGAR full-text for NHTSA exemption petition disclosures
    in 8-K and 10-Q filings.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT}
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    params = {
        "q": '"NHTSA" AND ("exemption petition" OR "exemption request")',
        "dateRange": "custom",
        "startdt": start_date,
        "enddt": end_date,
        "forms": "8-K,10-Q,10-K",
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
        record = {
            "filing_type": source.get("form_type", ""),
            "company_name": source.get("entity_name", ""),
            "filing_date": source.get("file_date", ""),
            "filing_url": source.get("file_url", ""),
            "description": source.get("display_names", [""])[0]
            if source.get("display_names")
            else "",
            "source_url": source.get("file_url", ""),
            "source_type": "SEC",
            "source_confidence": "secondary",
            "fetched_at": datetime.now().isoformat(),
        }
        results.append(record)

    # Save results
    if results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = RAW_DIR / f"nhtsa_exemption_edgar_{timestamp}.json"
        out_path.write_text(json.dumps(results, indent=2))
        print(f"Found {len(results)} NHTSA exemption mentions in EDGAR.")

    return results


def fetch_state_permits(state: str, days: int = 30) -> list[dict]:
    """
    Fetch permit data for a given state. Currently supports CA (DMV)
    and falls back to EDGAR search for other states.
    """
    state = state.upper()
    if state == "CA":
        return fetch_ca_dmv_permit_list()

    # For other states, search EDGAR for permit-related disclosures
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": USER_AGENT}
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    params = {
        "q": f'"autonomous" AND "permit" AND "{state}"',
        "dateRange": "custom",
        "startdt": start_date,
        "enddt": end_date,
        "forms": "8-K,10-Q",
    }

    response = httpx.get(
        EDGAR_EFTS_BASE, params=params, headers=headers, timeout=30
    )
    response.raise_for_status()
    data = response.json()

    hits = data.get("hits", {}).get("hits", [])
    results: list[dict] = []
    for hit in hits:
        source = hit.get("_source", {})
        record = {
            "state": state,
            "company_name": source.get("entity_name", ""),
            "filing_date": source.get("file_date", ""),
            "filing_url": source.get("file_url", ""),
            "source_url": source.get("file_url", ""),
            "source_type": "SEC",
            "source_confidence": "secondary",
            "fetched_at": datetime.now().isoformat(),
        }
        results.append(record)

    if results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = RAW_DIR / f"permits_{state}_{timestamp}.json"
        out_path.write_text(json.dumps(results, indent=2))
        print(f"Found {len(results)} permit-related filings for {state}.")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch AV testing permits and NHTSA exemption data"
    )
    parser.add_argument(
        "--state",
        type=str,
        default="CA",
        help="State abbreviation (default: CA)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Lookback window in days for EDGAR search",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max results from EDGAR full-text search",
    )
    args = parser.parse_args()

    print(f"--- Fetching permits for state: {args.state} ---")
    state_permits = fetch_state_permits(args.state, days=args.days)
    print(f"State permits: {len(state_permits)} records")

    print(f"\n--- Searching EDGAR for NHTSA exemption petitions (last {args.days} days) ---")
    exemptions = fetch_nhtsa_exemption_petitions_via_edgar(
        days=args.days, limit=args.limit
    )
    print(f"NHTSA exemption mentions: {len(exemptions)} records")
