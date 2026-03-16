"""
Safety Monitor -- Fetch Safety Reports
Query NHTSA Standing General Order (SGO) crash reports for AV incidents
and NHTSA recall data.
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path("data/raw/autonomous_vehicles/safety")

# NHTSA public APIs
NHTSA_COMPLAINTS_API = "https://api.nhtsa.gov/complaints/complaintsByVehicle"
NHTSA_RECALLS_API = "https://api.nhtsa.gov/recalls/recallsByVehicle"
NHTSA_SGO_URL = (
    "https://www.nhtsa.gov/technology-innovation/"
    "automated-vehicles/standing-general-order-crash-reporting"
)

USER_AGENT = os.getenv(
    "SEC_EDGAR_USER_AGENT",
    "AVRoboticsTracker research@example.com",
)

# AV-related manufacturers and models to track
AV_MAKES = [
    "WAYMO",
    "CRUISE",
    "TESLA",
    "ZOOX",
    "AURORA",
    "TUSIMPLE",
    "NURO",
    "MOTIONAL",
    "ARGO AI",
    "PONY.AI",
    "GATIK",
    "KODIAK",
]


def fetch_nhtsa_recalls(make: str, model_year: int = 0) -> list[dict]:
    """
    Fetch NHTSA recall data for a given vehicle make.

    Args:
        make: Vehicle manufacturer name (e.g. "TESLA", "WAYMO")
        model_year: Optional model year filter (0 = all years)
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    params = {"make": make}
    if model_year > 0:
        params["modelYear"] = str(model_year)

    headers = {"User-Agent": USER_AGENT}
    response = httpx.get(
        NHTSA_RECALLS_API, params=params, headers=headers, timeout=30
    )
    response.raise_for_status()
    data = response.json()

    results_list = data.get("results", [])
    records: list[dict] = []
    for item in results_list:
        record = {
            "make": item.get("Make", make),
            "model": item.get("Model", ""),
            "model_year": item.get("ModelYear", ""),
            "recall_number": item.get("NHTSACampaignNumber", ""),
            "recall_date": item.get("ReportReceivedDate", ""),
            "component": item.get("Component", ""),
            "summary": item.get("Summary", ""),
            "consequence": item.get("Consequence", ""),
            "remedy": item.get("Remedy", ""),
            "source_url": (
                f"https://www.nhtsa.gov/recalls?nhtsaId="
                f"{item.get('NHTSACampaignNumber', '')}"
            ),
            "source_type": "NHTSA",
            "source_confidence": "primary",
            "fetched_at": datetime.now().isoformat(),
        }
        records.append(record)

    return records


def fetch_nhtsa_complaints(make: str, model_year: int = 0) -> list[dict]:
    """
    Fetch NHTSA complaint data that may include AV-related incidents.

    Args:
        make: Vehicle manufacturer name
        model_year: Optional model year filter (0 = all years)
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    params = {"make": make}
    if model_year > 0:
        params["modelYear"] = str(model_year)

    headers = {"User-Agent": USER_AGENT}
    response = httpx.get(
        NHTSA_COMPLAINTS_API, params=params, headers=headers, timeout=30
    )
    response.raise_for_status()
    data = response.json()

    results_list = data.get("results", [])
    records: list[dict] = []
    for item in results_list:
        summary = item.get("Summary", "").lower()
        # Filter for AV/ADAS-related complaints
        av_keywords = [
            "autopilot", "self-driving", "autonomous", "adas",
            "cruise control", "lane keep", "auto steer",
            "full self", "automate",
        ]
        is_av_related = any(kw in summary for kw in av_keywords)
        if not is_av_related:
            continue

        record = {
            "make": item.get("Make", make),
            "model": item.get("Model", ""),
            "model_year": item.get("ModelYear", ""),
            "complaint_date": item.get("DateOfIncident", ""),
            "complaint_id": item.get("ODINumber", ""),
            "summary": item.get("Summary", ""),
            "crash": item.get("Crash", ""),
            "fire": item.get("Fire", ""),
            "injuries": item.get("NumberOfInjuries", 0),
            "deaths": item.get("NumberOfDeaths", 0),
            "source_url": (
                f"https://www.nhtsa.gov/vehicle/{make}/{item.get('Model', '')}"
            ),
            "source_type": "NHTSA",
            "source_confidence": "primary",
            "fetched_at": datetime.now().isoformat(),
        }
        records.append(record)

    return records


def fetch_sgo_crash_reports_page() -> dict:
    """
    Fetch the NHTSA SGO crash reporting page. NHTSA publishes AV crash
    data under the Standing General Order. The data is in downloadable
    files on this page.

    Returns metadata about the page fetch (the actual data requires
    downloading CSV/Excel files linked from the page).
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT}
    response = httpx.get(NHTSA_SGO_URL, headers=headers, timeout=30)
    response.raise_for_status()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"nhtsa_sgo_page_{timestamp}.html"
    raw_path.write_text(response.text, encoding="utf-8")

    # Try to extract download links
    download_links: list[str] = []
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if any(
                ext in href.lower()
                for ext in [".csv", ".xlsx", ".xls", ".pdf"]
            ):
                if "sgo" in href.lower() or "crash" in href.lower():
                    full_url = href
                    if not href.startswith("http"):
                        full_url = f"https://www.nhtsa.gov{href}"
                    download_links.append(full_url)
    except ImportError:
        print(
            "WARNING: beautifulsoup4 not installed. "
            "Raw HTML saved but download links not extracted."
        )

    result = {
        "page_url": NHTSA_SGO_URL,
        "download_links": download_links,
        "fetched_at": datetime.now().isoformat(),
        "source_type": "NHTSA",
        "source_confidence": "primary",
    }

    meta_path = RAW_DIR / f"nhtsa_sgo_meta_{timestamp}.json"
    meta_path.write_text(json.dumps(result, indent=2))

    return result


def run_safety_scan(days: int = 30, limit: int = 100) -> None:
    """Run a full safety scan across all tracked AV makes."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    all_recalls: list[dict] = []
    all_complaints: list[dict] = []

    for make in AV_MAKES:
        print(f"Scanning {make}...")
        try:
            recalls = fetch_nhtsa_recalls(make)
            all_recalls.extend(recalls)
            print(f"  Recalls: {len(recalls)}")
        except httpx.HTTPError as exc:
            print(f"  Recalls fetch failed for {make}: {exc}")

        try:
            complaints = fetch_nhtsa_complaints(make)
            all_complaints.extend(complaints)
            print(f"  AV-related complaints: {len(complaints)}")
        except httpx.HTTPError as exc:
            print(f"  Complaints fetch failed for {make}: {exc}")

    # Save aggregated results
    if all_recalls:
        recalls_path = RAW_DIR / f"recalls_all_{timestamp}.json"
        recalls_path.write_text(json.dumps(all_recalls[:limit], indent=2))
        print(f"\nTotal recalls saved: {min(len(all_recalls), limit)}")

    if all_complaints:
        complaints_path = RAW_DIR / f"complaints_av_{timestamp}.json"
        complaints_path.write_text(
            json.dumps(all_complaints[:limit], indent=2)
        )
        print(f"Total AV complaints saved: {min(len(all_complaints), limit)}")

    # Also fetch the SGO page
    print("\nFetching NHTSA SGO crash reporting page...")
    sgo = fetch_sgo_crash_reports_page()
    print(f"SGO download links found: {len(sgo.get('download_links', []))}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch NHTSA safety reports for AV companies"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Lookback window in days",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max records to save per category",
    )
    args = parser.parse_args()

    run_safety_scan(days=args.days, limit=args.limit)
