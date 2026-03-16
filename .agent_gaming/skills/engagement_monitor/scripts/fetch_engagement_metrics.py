"""
Fetch public launch engagement metrics for tracked Steam app IDs.
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
    ENGAGEMENT_METRICS_DIR,
    ensure_gaming_directory,
)
from super_agents.gaming.watchlist import build_tracked_titles_by_appid, load_seed_appids

OUT_DIR = ENGAGEMENT_METRICS_DIR
CURRENT_PLAYERS_URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"


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


def _fetch_current_players(appid: str) -> int | None:
    response = httpx.get(CURRENT_PLAYERS_URL, params={"appid": appid}, timeout=30, follow_redirects=True)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    payload = response.json()
    return payload.get("response", {}).get("player_count")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public engagement metrics")
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
            current_players = _fetch_current_players(appid)
        except httpx.HTTPError as exc:
            print(f"Skipping {appid}: {exc}")
            continue

        now = datetime.now(timezone.utc)
        tracked = tracked_titles.get(appid, {})
        records.append(
            {
                "metric_id": f"engagement_{appid}_{now.strftime('%Y%m%d_%H%M%S')}",
                "title": tracked.get("tracked_title", ""),
                "title_id": tracked.get("title_id", ""),
                "company_id": tracked.get("company_id", ""),
                "company_name": tracked.get("company_name", ""),
                "ticker": tracked.get("ticker", ""),
                "steam_app_id": appid,
                "snapshot_date": now.date().isoformat(),
                "metacritic_score": None,
                "opencritic_score": None,
                "steam_review_score_percent": None,
                "concurrent_players_current": current_players,
                "concurrent_players_peak_24h": None,
                "concurrent_players_peak_all_time": None,
                "estimated_launch_window_day": None,
                "source_url": f"https://store.steampowered.com/app/{appid}",
                "source_confidence": "primary",
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"engagement_metrics_{timestamp}.json"
    write_json(out_path, records)
    print(f"Saved {len(records)} engagement records to {out_path}")


if __name__ == "__main__":
    main()
