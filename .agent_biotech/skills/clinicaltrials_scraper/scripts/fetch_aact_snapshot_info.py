"""
AACT Snapshot Probe
Fetch metadata for the latest AACT flat-file snapshot and optionally probe the
download object to verify that it is reachable from the current environment.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

RAW_DIR = Path("data/raw/clinicaltrials")
AACT_DOWNLOADS_URL = "https://aact.ctti-clinicaltrials.org/downloads"
USER_AGENT = os.getenv("CLINICALTRIALS_USER_AGENT", os.getenv("SEC_EDGAR_USER_AGENT", "BiotechTracker research@example.com"))
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_latest_flatfile_snapshot() -> dict:
    """Return metadata for the latest AACT flat-file snapshot from the downloads page."""
    response = httpx.get(
        AACT_DOWNLOADS_URL,
        headers=REQUEST_HEADERS,
        timeout=30,
        follow_redirects=True,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.select(".snapshot-card.flatfiles")
    if not cards:
        raise RuntimeError("Could not find the AACT flatfiles snapshot card on the downloads page.")

    card = cards[0]
    file_name = card.select_one(".detail-value").get_text(strip=True)
    detail_values = [node.get_text(strip=True) for node in card.select(".detail-value")]
    export_date = card.select_one(".snapshot-date").get_text(strip=True).replace("Last Exported:", "").strip()
    download_link = card.select_one("a.snapshots-action-button.primary")
    if download_link is None:
        raise RuntimeError("Could not find the AACT flatfiles download link.")

    return {
        "source_page": AACT_DOWNLOADS_URL,
        "snapshot_type": "flatfiles",
        "export_date": export_date,
        "file_name": file_name,
        "size": detail_values[1] if len(detail_values) > 1 else "",
        "download_url": download_link["href"],
        "fetched_at": datetime.now().isoformat(),
    }


def probe_download(url: str) -> dict:
    """Verify the download object is reachable without downloading the full archive."""
    headers = {
        "User-Agent": USER_AGENT,
        "Range": "bytes=0-0",
    }
    response = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
    return {
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "content_length": response.headers.get("content-length", ""),
        "accept_ranges": response.headers.get("accept-ranges", ""),
        "final_url": str(response.url),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch metadata for the latest AACT flatfile snapshot")
    parser.add_argument("--probe-download", action="store_true", help="Probe the remote object with a range request")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = fetch_latest_flatfile_snapshot()
    if args.probe_download:
        snapshot["download_probe"] = probe_download(snapshot["download_url"])

    out_path = RAW_DIR / "aact_latest_snapshot.json"
    out_path.write_text(json.dumps(snapshot, indent=2))
    print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    main()
