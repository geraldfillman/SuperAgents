"""Program calendar helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from .io_utils import load_json_records, write_json
from .paths import DASHBOARDS_DIR, ensure_directory, project_path

DEFAULT_PROCESSED_ROOT = project_path("data", "processed")
COMPLETED_STATUSES = {"complete", "completed", "closed", "cancelled", "canceled"}


def parse_date(value: str) -> date | None:
    """Parse a small set of supported date formats."""
    if not value:
        return None

    candidate = value.strip()
    for parser in (datetime.fromisoformat,):
        try:
            return parser(candidate).date()
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d", "%Y-%m", "%B %d, %Y", "%b %d, %Y"):
        try:
            parsed = datetime.strptime(candidate, fmt)
        except ValueError:
            continue
        if fmt == "%Y-%m":
            return parsed.date().replace(day=1)
        return parsed.date()

    return None


def _normalize_milestone(record: dict) -> dict | None:
    raw_date = record.get("expected_date") or record.get("window_start")
    parsed = parse_date(raw_date)
    if parsed is None:
        return None
    return {
        "date": parsed.isoformat(),
        "entry_type": "program_milestone",
        "headline": record.get("milestone_name") or record.get("evidence_summary") or record.get("milestone_type", ""),
        "company_name": record.get("company_name", ""),
        "ticker": record.get("ticker", ""),
        "system_name": record.get("system_name", ""),
        "status": record.get("status", ""),
        "source_url": record.get("source_url", ""),
        "source_type": record.get("source_type", ""),
        "source_confidence": record.get("source_confidence", ""),
    }


def _normalize_test_event(record: dict) -> dict | None:
    parsed = parse_date(record.get("event_date", ""))
    if parsed is None:
        return None
    return {
        "date": parsed.isoformat(),
        "entry_type": "test_event",
        "headline": record.get("event_name", ""),
        "company_name": record.get("company_name", ""),
        "ticker": record.get("ticker", ""),
        "system_name": record.get("system_name", ""),
        "status": record.get("outcome", ""),
        "source_url": record.get("source_url", ""),
        "source_type": record.get("source_type", ""),
        "source_confidence": record.get("source_confidence", ""),
    }


def _normalize_contract_award(record: dict) -> dict | None:
    raw_date = record.get("start_date") or record.get("award_date")
    parsed = parse_date(raw_date or "")
    if parsed is None:
        return None
    return {
        "date": parsed.isoformat(),
        "entry_type": "contract_award",
        "headline": record.get("description") or record.get("award_number", ""),
        "company_name": record.get("company_name", ""),
        "ticker": record.get("ticker", ""),
        "system_name": record.get("system_name", ""),
        "status": record.get("contract_status", ""),
        "source_url": record.get("source_url", ""),
        "source_type": record.get("source_type", ""),
        "source_confidence": record.get("source_confidence", ""),
    }


def load_calendar_entries(processed_root: Path | None = None) -> list[dict]:
    """Load normalized calendar entries from processed directories."""
    root = processed_root or DEFAULT_PROCESSED_ROOT
    entries: list[dict] = []

    for record in load_json_records(root / "program_milestones"):
        normalized = _normalize_milestone(record)
        if normalized is not None:
            entries.append(normalized)

    for record in load_json_records(root / "test_events"):
        normalized = _normalize_test_event(record)
        if normalized is not None:
            entries.append(normalized)

    for record in load_json_records(root / "contract_awards"):
        normalized = _normalize_contract_award(record)
        if normalized is not None:
            entries.append(normalized)

    entries.sort(key=lambda item: (item["date"], item["entry_type"], item["headline"]))
    return entries


def build_program_calendar(days: int = 90, processed_root: Path | None = None) -> dict[str, list[dict]]:
    """Build upcoming and overdue program views."""
    today = date.today()
    cutoff = today + timedelta(days=days)

    upcoming: list[dict] = []
    overdue: list[dict] = []
    for entry in load_calendar_entries(processed_root=processed_root):
        entry_date = parse_date(entry["date"])
        if entry_date is None:
            continue

        normalized_status = str(entry.get("status", "")).strip().lower()
        if today <= entry_date <= cutoff:
            upcoming.append(entry)
        elif entry["entry_type"] != "contract_award" and entry_date < today and normalized_status not in COMPLETED_STATUSES:
            overdue.append(entry)

    return {"upcoming": upcoming, "overdue": overdue}


def write_calendar_snapshot(calendar_payload: dict[str, list[dict]], days: int, dashboards_dir: Path | None = None) -> list[Path]:
    """Persist the calendar payload to dashboard-friendly JSON files."""
    destination = ensure_directory(dashboards_dir or DASHBOARDS_DIR)
    upcoming_path = destination / f"program_calendar_{days}d.json"
    overdue_path = destination / "program_calendar_overdue.json"
    write_json(upcoming_path, calendar_payload["upcoming"])
    write_json(overdue_path, calendar_payload["overdue"])
    return [upcoming_path, overdue_path]
