"""Calendar helpers for cybersecurity due-date views."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


def _parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _severity_rank(value: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "info": 3}.get(value, 4)


def build_patch_calendar(
    records: list[dict[str, Any]],
    *,
    window_days: int,
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    """Build due-date events from normalized KEV records."""
    today = reference_date or date.today()
    end = today + timedelta(days=window_days)
    events: list[dict[str, Any]] = []

    for record in records:
        due = _parse_iso_date(str(record.get("due_date", "")))
        if due is None:
            continue
        if not today <= due <= end:
            continue

        events.append(
            {
                "date": due.isoformat(),
                "event_type": "patch_due",
                "severity": record.get("severity", "medium"),
                "cve_id": record.get("cve_id", ""),
                "asset": record.get("asset", ""),
                "vendor": record.get("vendor", ""),
                "product": record.get("product", ""),
                "detail": record.get("required_action", ""),
                "watchlist_match": record.get("watchlist_match", False),
                "source_url": record.get("source_url", ""),
                "source_confidence": record.get("source_confidence", "primary"),
            }
        )

    events.sort(key=lambda event: (event.get("date", ""), _severity_rank(event.get("severity", ""))))
    return events
