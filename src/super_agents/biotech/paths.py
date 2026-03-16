"""Filesystem helpers for biotech scripts."""

from __future__ import annotations

from pathlib import Path

from super_agents.common.paths import DASHBOARDS_DIR, DATA_DIR, PROJECT_ROOT, ensure_directory, project_path, slugify

BIOTECH_COMPANY_WATCHLIST_PATH = project_path("data", "seeds", "biotech_company_watchlist.csv")
BIOTECH_PRODUCT_WATCHLIST_PATH = project_path("data", "seeds", "biotech_product_watchlist.csv")

RAW_FDA_DIR = DATA_DIR / "raw" / "fda"
RAW_CLINICALTRIALS_DIR = DATA_DIR / "raw" / "clinicaltrials"
RAW_SEC_DIR = DATA_DIR / "raw" / "sec"
PROCESSED_DIR = DATA_DIR / "processed"

DRUG_APPROVALS_RAW_DIR = RAW_FDA_DIR / "drug_approvals"
DEVICE_CLEARANCES_RAW_DIR = RAW_FDA_DIR / "device_clearances"
ADVISORY_CALENDAR_RAW_DIR = RAW_FDA_DIR / "advisory_calendar"
POSTMARKETING_RAW_DIR = RAW_FDA_DIR / "postmarketing"


def ensure_biotech_directory(path: Path) -> Path:
    """Create a directory if needed and return it."""
    return ensure_directory(path)
