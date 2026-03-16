"""
Fetch public Steam storefront metadata for tracked app IDs.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.gaming.io_utils import write_json
from super_agents.gaming.paths import (
    DEFAULT_APPIDS_FILE,
    DEFAULT_TRACKED_FILE,
    STOREFRONT_METRICS_DIR,
    ensure_gaming_directory,
)
from super_agents.gaming.watchlist import build_tracked_titles_by_appid, load_seed_appids

OUT_DIR = STOREFRONT_METRICS_DIR
STORE_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"


def _load_appids(appid: str | None, appids_file: Path | None, batch: bool) -> list[str]:
    if appid:
        return [appid]

    file_path = appids_file or DEFAULT_APPIDS_FILE
    if file_path.exists():
        return [
            line.strip()
            for line in file_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

    if batch:
        return load_seed_appids()

    return []


def _fetch_appdetails(appid: str) -> dict | None:
    response = httpx.get(STORE_APPDETAILS_URL, params={"appids": appid}, timeout=30, follow_redirects=True)
    response.raise_for_status()
    payload = response.json()
    app_payload = payload.get(str(appid), {})
    if not app_payload.get("success"):
        return None
    return app_payload.get("data", {})


def _transform(appid: str, data: dict, tracked_titles: dict[str, dict]) -> dict:
    now = datetime.now(timezone.utc)
    tracked = tracked_titles.get(appid, {})
    release_date = data.get("release_date", {}).get("date", "")
    genres = [genre.get("description", "") for genre in data.get("genres", [])]
    categories = [category.get("description", "") for category in data.get("categories", [])]
    return {
        "metric_id": f"steam_{appid}_{now.strftime('%Y%m%d')}",
        "title": tracked.get("tracked_title") or data.get("name", ""),
        "title_id": tracked.get("title_id", ""),
        "company_id": tracked.get("company_id", ""),
        "company_name": tracked.get("company_name", ""),
        "ticker": tracked.get("ticker", ""),
        "storefront": "steam",
        "steam_app_id": appid,
        "snapshot_date": now.date().isoformat(),
        "release_date": release_date,
        "follower_count": None,
        "wishlist_rank": None,
        "review_count": None,
        "review_score_percent": None,
        "tags": genres + categories,
        "developers": data.get("developers", []),
        "publishers": data.get("publishers", []),
        "platforms": data.get("platforms", {}),
        "source_url": f"https://store.steampowered.com/app/{appid}",
        "source_confidence": "primary",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public storefront metrics")
    parser.add_argument("--appid", type=str, help="Single Steam app ID")
    parser.add_argument("--appids-file", type=Path, help="File with one app ID per line")
    parser.add_argument("--tracked-file", type=Path, default=DEFAULT_TRACKED_FILE, help="Tracked studios JSON file")
    parser.add_argument("--batch", action="store_true", help="Process a batch file of app IDs")
    args = parser.parse_args()

    appids = _load_appids(args.appid, args.appids_file, args.batch)
    if not appids:
        print("No app IDs provided. Use --appid or create data/raw/gaming/appids.txt and pass --batch.")
        return

    ensure_gaming_directory(OUT_DIR)
    tracked_titles = build_tracked_titles_by_appid(args.tracked_file)
    records: list[dict] = []
    for appid in appids:
        try:
            payload = _fetch_appdetails(appid)
        except httpx.HTTPError as exc:
            print(f"Skipping {appid}: {exc}")
            continue
        if payload is None:
            print(f"Skipping {appid}: no storefront data returned")
            continue
        records.append(_transform(appid, payload, tracked_titles))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"storefront_metrics_{timestamp}.json"
    write_json(out_path, records)
    print(f"Saved {len(records)} storefront records to {out_path}")


if __name__ == "__main__":
    main()
