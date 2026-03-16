"""Filesystem helpers for cybersecurity scripts."""

from __future__ import annotations

from pathlib import Path

from super_agents.common.paths import DASHBOARDS_DIR, DATA_DIR, ensure_directory, project_path

CYBERSECURITY_ASSET_WATCHLIST_PATH = project_path(
    "data", "seeds", "cybersecurity_asset_watchlist.csv"
)
CYBERSECURITY_ORG_WATCHLIST_PATH = project_path(
    "data", "seeds", "cybersecurity_org_watchlist.csv"
)

RAW_CYBERSECURITY_DIR = DATA_DIR / "raw" / "cybersecurity"
PROCESSED_CYBERSECURITY_DIR = DATA_DIR / "processed" / "cybersecurity"

KEV_RAW_DIR = RAW_CYBERSECURITY_DIR / "kev"
KEV_PROCESSED_DIR = PROCESSED_CYBERSECURITY_DIR / "kev"
CYBERSECURITY_CALENDAR_DIR = PROCESSED_CYBERSECURITY_DIR / "calendars"


def ensure_cybersecurity_directory(path: Path) -> Path:
    """Create a directory if needed and return it."""
    return ensure_directory(path)
