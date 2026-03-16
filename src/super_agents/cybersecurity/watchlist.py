"""Cybersecurity watchlist loaders."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import CYBERSECURITY_ASSET_WATCHLIST_PATH, CYBERSECURITY_ORG_WATCHLIST_PATH


@dataclass(frozen=True)
class AssetRecord:
    """Tracked cybersecurity asset metadata."""

    vendor: str = ""
    product: str = ""
    cve_id: str = ""
    priority: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class OrganizationRecord:
    """Tracked cybersecurity company metadata."""

    company_name: str
    ticker: str = ""
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


def load_asset_watchlist(path: Path | None = None) -> list[AssetRecord]:
    """Load tracked cyber assets such as vendors, products, and CVEs."""
    rows = _load_rows(path or CYBERSECURITY_ASSET_WATCHLIST_PATH)
    return [AssetRecord(**row) for row in rows]


def load_org_watchlist(path: Path | None = None) -> list[OrganizationRecord]:
    """Load tracked cybersecurity companies."""
    rows = _load_rows(path or CYBERSECURITY_ORG_WATCHLIST_PATH)
    return [OrganizationRecord(**row) for row in rows]


def find_asset(
    *,
    cve_id: str | None = None,
    vendor: str | None = None,
    product: str | None = None,
    assets: list[AssetRecord] | None = None,
) -> AssetRecord | None:
    """Return the first watchlist asset matching the supplied identifiers."""
    pool = assets or load_asset_watchlist()
    normalized_cve = (cve_id or "").strip().upper()
    normalized_vendor = (vendor or "").strip().lower()
    normalized_product = (product or "").strip().lower()

    for asset in pool:
        if normalized_cve and asset.cve_id.strip().upper() == normalized_cve:
            return asset
        if normalized_vendor and asset.vendor.strip().lower() == normalized_vendor:
            if not normalized_product or asset.product.strip().lower() == normalized_product:
                return asset
    return None
