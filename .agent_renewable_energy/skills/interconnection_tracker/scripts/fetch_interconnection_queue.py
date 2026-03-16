"""
Interconnection Tracker -- Fetch Interconnection Queue
Query the EIA API for generator interconnection data and scrape PJM queue.
"""

import os
import json
import argparse
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path("data/raw/renewable_energy/interconnection")
EIA_API_KEY = os.getenv("EIA_API_KEY", "")
EIA_BASE_URL = "https://api.eia.gov/v2/electricity/operating-generator-capacity/data/"
PJM_QUEUE_URL = "https://services.pjm.com/api/interconnection/queue"

USER_AGENT = os.getenv(
    "RENEWABLE_ENERGY_USER_AGENT",
    "RenewableEnergyTracker research@example.com",
)


def fetch_eia_interconnection(
    iso: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    Fetch generator capacity / interconnection data from the EIA API.

    Args:
        iso: Filter by ISO region (e.g. PJM, MISO, CAISO, ERCOT)
        status: Filter by status (e.g. proposed, under_construction, operating)
        limit: Maximum records to return
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    params: dict = {
        "api_key": EIA_API_KEY,
        "frequency": "annual",
        "data[0]": "nameplate-capacity-mw",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": limit,
    }

    if iso:
        params["facets[balancing_authority_code][]"] = iso.upper()
    if status:
        params["facets[status][]"] = status

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    response = httpx.get(EIA_BASE_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    records = data.get("response", {}).get("data", [])

    results = []
    for record in records:
        results.append({
            "queue_id": record.get("plantid", ""),
            "plant_name": record.get("plantName", ""),
            "state": record.get("stateid", ""),
            "balancing_authority": record.get("balancing_authority_code", ""),
            "technology": record.get("technology", ""),
            "nameplate_capacity_mw": record.get("nameplate-capacity-mw"),
            "status": record.get("status", ""),
            "period": record.get("period", ""),
            "source_url": EIA_BASE_URL,
            "source_type": "EIA",
            "source_confidence": "primary",
        })

    # Save raw response
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    iso_tag = iso or "all"
    raw_path = RAW_DIR / f"eia_interconnection_{iso_tag}_{timestamp}.json"
    raw_path.write_text(json.dumps(results, indent=2))
    print(f"Saved {len(results)} EIA interconnection records to {raw_path}")

    return results


def fetch_pjm_queue(status: str | None = None, limit: int = 100) -> list[dict]:
    """
    Fetch PJM interconnection queue data.

    Args:
        status: Filter by queue status
        limit: Maximum records to return
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    params: dict = {"rowCount": limit}
    if status:
        params["status"] = status

    response = httpx.get(PJM_QUEUE_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    records = data if isinstance(data, list) else data.get("items", [])

    results = []
    for record in records:
        results.append({
            "queue_id": record.get("queueNumber", ""),
            "project_name": record.get("projectName", ""),
            "state": record.get("state", ""),
            "county": record.get("county", ""),
            "fuel_type": record.get("fuelType", ""),
            "capacity_mw": record.get("mw"),
            "status": record.get("status", ""),
            "queue_date": record.get("queueDate", ""),
            "in_service_date": record.get("commercialOperationDate", ""),
            "source_url": PJM_QUEUE_URL,
            "source_type": "PJM",
            "source_confidence": "primary",
        })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"pjm_queue_{timestamp}.json"
    raw_path.write_text(json.dumps(results, indent=2))
    print(f"Saved {len(results)} PJM queue records to {raw_path}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch interconnection queue data from EIA and PJM"
    )
    parser.add_argument("--iso", type=str, help="ISO region filter (PJM, MISO, CAISO, ERCOT, SPP, NYISO, ISONE)")
    parser.add_argument("--status", type=str, help="Status filter")
    parser.add_argument("--limit", type=int, default=100, help="Max records to fetch")
    parser.add_argument("--pjm-only", action="store_true", help="Only fetch PJM queue")
    args = parser.parse_args()

    if args.pjm_only:
        results = fetch_pjm_queue(status=args.status, limit=args.limit)
        print(f"Fetched {len(results)} PJM queue entries")
    else:
        results = fetch_eia_interconnection(
            iso=args.iso, status=args.status, limit=args.limit
        )
        print(f"Fetched {len(results)} EIA interconnection records")

        if args.iso and args.iso.upper() == "PJM":
            pjm_results = fetch_pjm_queue(status=args.status, limit=args.limit)
            print(f"Fetched {len(pjm_results)} PJM queue entries")
