"""Gaming seed watchlist loaders and adapters."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import GAMING_STUDIO_WATCHLIST_PATH


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value.strip().upper()).strip("_") or "UNKNOWN"


@dataclass(frozen=True)
class StudioRecord:
    """Tracked gaming studio metadata."""

    company_name: str
    ticker: str
    sec_cik: str = ""
    country: str = ""
    primary_focus: str = ""
    priority: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TitleRecord:
    """Tracked gaming title metadata."""

    company_name: str
    ticker: str
    title_name: str
    title_id: str = ""
    steam_app_id: str = ""
    platform: str = ""
    release_window: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _load_seed_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_studio_watchlist(path: Path | None = None) -> list[StudioRecord]:
    """Load studios from the seed watchlist, de-duplicated by ticker/company."""
    rows = _load_seed_rows(path or GAMING_STUDIO_WATCHLIST_PATH)
    seen: dict[tuple[str, str], StudioRecord] = {}
    for row in rows:
        key = (row.get("ticker", "").strip().upper(), row.get("company_name", "").strip().lower())
        if key in seen:
            continue
        seen[key] = StudioRecord(
            company_name=row.get("company_name", ""),
            ticker=row.get("ticker", ""),
            sec_cik=row.get("sec_cik", ""),
            country=row.get("country", ""),
            primary_focus=row.get("primary_focus", ""),
            priority=row.get("priority", ""),
            notes=row.get("notes", ""),
        )
    return list(seen.values())


def load_title_watchlist(path: Path | None = None) -> list[TitleRecord]:
    """Load tracked titles from the seed watchlist."""
    rows = _load_seed_rows(path or GAMING_STUDIO_WATCHLIST_PATH)
    records: list[TitleRecord] = []
    for row in rows:
        title_name = row.get("title_name", "")
        if not title_name:
            continue
        records.append(
            TitleRecord(
                company_name=row.get("company_name", ""),
                ticker=row.get("ticker", ""),
                title_name=title_name,
                title_id=row.get("title_id", ""),
                steam_app_id=row.get("steam_app_id", ""),
                platform=row.get("platform", ""),
                release_window=row.get("release_window", ""),
                notes=row.get("notes", ""),
            )
        )
    return records


def load_seed_appids(path: Path | None = None) -> list[str]:
    """Load non-empty Steam app IDs from the seed watchlist."""
    appids: list[str] = []
    for record in load_title_watchlist(path):
        appid = str(record.steam_app_id).strip()
        if appid:
            appids.append(appid)
    return appids


def _payload_to_titles_by_appid(payload: list[dict]) -> dict[str, dict]:
    by_appid: dict[str, dict] = {}
    for studio in payload:
        if not isinstance(studio, dict):
            continue
        company_id = studio.get("company_id") or _slug(studio.get("ticker", "") or studio.get("company_name", ""))
        for title in studio.get("titles", []):
            if not isinstance(title, dict):
                continue
            app_id = title.get("steam_app_id")
            if not app_id:
                continue
            title_name = title.get("game_title", "")
            by_appid[str(app_id)] = {
                "title_id": title.get("title_id") or f"{company_id}_{_slug(title_name)}",
                "tracked_title": title_name,
                "company_id": company_id,
                "company_name": studio.get("company_name", ""),
                "ticker": studio.get("ticker", ""),
            }
    return by_appid


def _load_json_payload(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def build_tracked_studios_payload(path: Path | None = None) -> list[dict]:
    """Return the nested studio/title payload used by the legacy gaming scripts."""
    if path and path.exists():
        if path.suffix.lower() == ".json":
            return _load_json_payload(path)
        if path.suffix.lower() == ".csv":
            rows = _load_seed_rows(path)
        else:
            rows = []
    else:
        rows = _load_seed_rows(GAMING_STUDIO_WATCHLIST_PATH)

    grouped: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row.get("ticker", "").strip().upper(), row.get("company_name", "").strip().lower())
        studio = grouped.get(key)
        if studio is None:
            company_id = _slug(row.get("ticker", "") or row.get("company_name", ""))
            studio = {
                "company_id": company_id,
                "company_name": row.get("company_name", ""),
                "ticker": row.get("ticker", ""),
                "sec_cik": row.get("sec_cik", ""),
                "country": row.get("country", ""),
                "lead_focus": row.get("primary_focus", ""),
                "notes": row.get("notes", ""),
                "titles": [],
            }
            grouped[key] = studio

        title_name = row.get("title_name", "")
        if title_name:
            studio["titles"].append(
                {
                    "game_title": title_name,
                    "title_id": row.get("title_id", "") or f"{studio['company_id']}_{_slug(title_name)}",
                    "steam_app_id": row.get("steam_app_id", ""),
                    "platform": row.get("platform", ""),
                    "release_window": row.get("release_window", ""),
                    "notes": row.get("notes", ""),
                }
            )

    return list(grouped.values())


def build_tracked_titles_by_appid(path: Path | None = None) -> dict[str, dict]:
    """Return tracked-title metadata keyed by Steam app ID."""
    payload = build_tracked_studios_payload(path)
    return _payload_to_titles_by_appid(payload)
