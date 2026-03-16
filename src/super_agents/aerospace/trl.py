"""TRL helpers for manual evidence capture."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from .io_utils import write_json
from .paths import ensure_directory, project_path, slugify

TRL_SIGNAL_DIR = project_path("data", "processed", "trl_signals")
TEST_EVENT_DIR = project_path("data", "processed", "test_events")
PROGRAM_MILESTONE_DIR = project_path("data", "processed", "program_milestones")


def validate_trl_level(level: int) -> int:
    """Ensure a TRL level falls inside the standard 1-9 range."""
    if not 1 <= level <= 9:
        raise ValueError("TRL level must be between 1 and 9")
    return level


def build_trl_signal(
    *,
    system_name: str,
    trl_level: int,
    evidence_summary: str,
    company_name: str = "",
    ticker: str = "",
    milestone_type: str = "test_event",
    event_date: str | None = None,
    expected_date: str = "",
    source_url: str = "",
    source_type: str = "manual",
    source_confidence: str = "manual",
    status: str = "observed",
) -> dict:
    """Build a normalized TRL evidence record."""
    validated_level = validate_trl_level(trl_level)
    return {
        "system_name": system_name,
        "company_name": company_name,
        "ticker": ticker,
        "trl_level": validated_level,
        "evidence_summary": evidence_summary,
        "milestone_type": milestone_type,
        "event_date": event_date or date.today().isoformat(),
        "expected_date": expected_date,
        "status": status,
        "source_url": source_url,
        "source_type": source_type,
        "source_confidence": source_confidence,
        "recorded_at": datetime.now().isoformat(),
    }


def build_test_event(signal: dict) -> dict:
    """Convert a TRL signal into a test-event record."""
    return {
        "system_name": signal["system_name"],
        "company_name": signal.get("company_name", ""),
        "ticker": signal.get("ticker", ""),
        "event_name": signal["evidence_summary"],
        "event_type": signal.get("milestone_type", "test_event"),
        "event_date": signal.get("event_date", ""),
        "outcome": signal.get("status", ""),
        "source_url": signal.get("source_url", ""),
        "source_type": signal.get("source_type", ""),
        "source_confidence": signal.get("source_confidence", ""),
    }


def build_program_milestone(signal: dict) -> dict | None:
    """Create a forward-looking milestone when an expected date is present."""
    expected_date = signal.get("expected_date", "")
    if not expected_date:
        return None

    return {
        "system_name": signal["system_name"],
        "company_name": signal.get("company_name", ""),
        "ticker": signal.get("ticker", ""),
        "milestone_type": signal.get("milestone_type", "milestone"),
        "milestone_name": signal["evidence_summary"],
        "expected_date": expected_date,
        "status": "planned",
        "source_url": signal.get("source_url", ""),
        "source_type": signal.get("source_type", ""),
        "source_confidence": signal.get("source_confidence", ""),
    }


def persist_trl_bundle(signal: dict) -> list[Path]:
    """Write the TRL signal and related records to disk."""
    system_slug = slugify(signal["system_name"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    signal_path = ensure_directory(TRL_SIGNAL_DIR) / f"trl_signal_{system_slug}_{timestamp}.json"
    write_json(signal_path, signal)

    test_event_path = ensure_directory(TEST_EVENT_DIR) / f"test_event_{system_slug}_{timestamp}.json"
    write_json(test_event_path, build_test_event(signal))

    written_paths = [signal_path, test_event_path]
    milestone = build_program_milestone(signal)
    if milestone is not None:
        milestone_path = ensure_directory(PROGRAM_MILESTONE_DIR) / f"program_milestone_{system_slug}_{timestamp}.json"
        write_json(milestone_path, milestone)
        written_paths.append(milestone_path)

    return written_paths
