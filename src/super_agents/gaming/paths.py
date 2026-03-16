"""Filesystem helpers for gaming scripts."""

from __future__ import annotations

from pathlib import Path

from super_agents.common.paths import DASHBOARDS_DIR, DATA_DIR, PROJECT_ROOT, ensure_directory, project_path, slugify

GAMING_STUDIO_WATCHLIST_PATH = project_path("data", "seeds", "gaming_studio_watchlist.csv")

RAW_GAMING_DIR = DATA_DIR / "raw" / "gaming"
PROCESSED_DIR = DATA_DIR / "processed"

STOREFRONT_METRICS_DIR = PROCESSED_DIR / "storefront_metrics"
ENGAGEMENT_METRICS_DIR = PROCESSED_DIR / "engagement_metrics"
STUDIO_SCREENER_DIR = PROCESSED_DIR / "studio_screener"
GAMING_SEC_CATALYSTS_DIR = PROCESSED_DIR / "gaming_sec_catalysts"
CERTIFICATIONS_DIR = PROCESSED_DIR / "certifications"
RELEASE_EVENTS_DIR = PROCESSED_DIR / "release_events"

DEFAULT_APPIDS_FILE = RAW_GAMING_DIR / "appids.txt"
DEFAULT_TRACKED_FILE = RAW_GAMING_DIR / "studio_candidates.json"


def ensure_gaming_directory(path: Path) -> Path:
    """Create a directory if needed and return it."""
    return ensure_directory(path)
