"""Filesystem helpers for fintech scripts."""

from __future__ import annotations

from pathlib import Path

from super_agents.common.paths import DATA_DIR, ensure_directory, project_path

FINTECH_COMPANY_WATCHLIST_PATH = project_path("data", "seeds", "fintech_company_watchlist.csv")

RAW_FINTECH_DIR = DATA_DIR / "raw" / "fintech"
LICENSES_RAW_DIR = RAW_FINTECH_DIR / "licenses"
ADOPTION_RAW_DIR = RAW_FINTECH_DIR / "adoption"
PARTNERSHIPS_RAW_DIR = RAW_FINTECH_DIR / "partnerships"
ENFORCEMENT_RAW_DIR = RAW_FINTECH_DIR / "enforcement"


def ensure_fintech_directory(path: Path) -> Path:
    """Create a directory if needed and return it."""
    return ensure_directory(path)
