"""Fintech seed watchlist loaders."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import FINTECH_COMPANY_WATCHLIST_PATH


@dataclass(frozen=True)
class CompanyRecord:
    """Tracked fintech company metadata."""

    company_name: str
    ticker: str
    cik: str = ""
    primary_focus: str = ""
    priority: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_company_watchlist(path: Path | None = None) -> list[CompanyRecord]:
    """Load the tracked fintech company watchlist."""
    rows = _load_rows(path or FINTECH_COMPANY_WATCHLIST_PATH)
    return [CompanyRecord(**row) for row in rows]


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
