"""Seed watchlist loaders."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import project_path

COMPANY_WATCHLIST_PATH = project_path("data", "seeds", "company_watchlist.csv")
SYSTEM_WATCHLIST_PATH = project_path("data", "seeds", "system_watchlist.csv")


@dataclass(frozen=True)
class CompanyRecord:
    """Tracked company metadata."""

    company_name: str
    ticker: str
    cik: str = ""
    cage_code: str = ""
    ueid: str = ""
    primary_domain: str = ""
    primary_customer: str = ""
    priority: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class SystemRecord:
    """Tracked system metadata."""

    company_name: str
    ticker: str
    system_name: str
    domain: str
    system_type: str = ""
    primary_customer: str = ""
    current_status: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary."""
        return asdict(self)


def _load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_company_watchlist(path: Path | None = None) -> list[CompanyRecord]:
    """Load the tracked company watchlist."""
    rows = _load_rows(path or COMPANY_WATCHLIST_PATH)
    return [CompanyRecord(**row) for row in rows]


def load_system_watchlist(path: Path | None = None) -> list[SystemRecord]:
    """Load the tracked system watchlist."""
    rows = _load_rows(path or SYSTEM_WATCHLIST_PATH)
    return [SystemRecord(**row) for row in rows]


def find_company(
    *,
    ticker: str | None = None,
    company_name: str | None = None,
    companies: list[CompanyRecord] | None = None,
) -> CompanyRecord | None:
    """Return the first company matching the provided ticker or company name."""
    pool = companies or load_company_watchlist()

    normalized_ticker = (ticker or "").strip().upper()
    normalized_name = (company_name or "").strip().lower()
    for company in pool:
        if normalized_ticker and company.ticker.upper() == normalized_ticker:
            return company
        if normalized_name and company.company_name.lower() == normalized_name:
            return company
    return None
