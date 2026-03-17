"""events.py

Lightweight file-based event bus for Super_Agents.

Phase 1 design: write JSON event files to data/events/ directory so that:
  - Agents emit events after completing work
  - Dashboard polls for new events since a given timestamp
  - No external dependencies, no daemon processes required

Future phases:
  - Phase 2: write to UnifiedStore events table alongside files
  - Phase 3: Redis pub/sub or SSE for real-time streaming

Usage:
    bus = EventBus()
    bus.emit("run_completed", {"agent": "biotech", "run_id": "abc123"})

    new_events = bus.poll(since="2026-03-16T00:00:00Z")
    for event in new_events:
        print(event.event_type, event.payload)
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from super_agents.common.paths import DATA_DIR, ensure_directory

logger = logging.getLogger(__name__)

DEFAULT_EVENTS_DIR = DATA_DIR / "events"

# Accepted event_type values — open-ended but documented
KNOWN_EVENT_TYPES = frozenset(
    {
        "run_completed",
        "run_failed",
        "finding_added",
        "signal_received",
        "agent_started",
        "agent_stopped",
        "alert_triggered",
        "metric_recorded",
    }
)


# ---------------------------------------------------------------------------
# Event dataclass — immutable
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Event:
    """A single emitted event."""

    event_id: str
    event_type: str
    payload: dict[str, Any]
    emitted_at: str  # ISO-8601 UTC


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------

class EventBus:
    """File-based event bus.

    Events are written as individual JSON files named:
        <emitted_at_iso>_<event_type>_<event_id>.json

    The timestamp prefix enables efficient sorted glob scanning in poll().
    """

    def __init__(self, events_dir: Path | str = DEFAULT_EVENTS_DIR) -> None:
        self._events_dir = Path(events_dir)
        ensure_directory(self._events_dir)

    # -- Emit ---------------------------------------------------------------

    def emit(self, event_type: str, payload: dict[str, Any]) -> Event:
        """Write an event to the events directory.

        Args:
            event_type: Logical event name (e.g. "run_completed").
            payload:    Arbitrary JSON-serialisable dict with event data.

        Returns:
            The immutable Event that was written to disk.

        Raises:
            ValueError: If event_type is empty or payload is not a dict.
            OSError:    If the file cannot be written.
        """
        if not event_type or not isinstance(event_type, str):
            raise ValueError("event_type must be a non-empty string")
        if not isinstance(payload, dict):
            raise ValueError(f"payload must be a dict, got {type(payload).__name__}")

        if event_type not in KNOWN_EVENT_TYPES:
            logger.warning("emit: unknown event_type %r (still accepted)", event_type)

        event_id = str(uuid.uuid4())
        emitted_at = _now_iso()
        safe_type = _safe_filename(event_type)
        filename = f"{emitted_at.replace(':', '-')}_{safe_type}_{event_id[:8]}.json"
        file_path = self._events_dir / filename

        event_dict = {
            "event_id": event_id,
            "event_type": event_type,
            "payload": payload,
            "emitted_at": emitted_at,
        }

        try:
            file_path.write_text(
                json.dumps(event_dict, indent=2, default=str),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("emit: failed to write event %s: %s", event_id, exc)
            raise

        logger.debug("emit: %s → %s", event_type, filename)
        return Event(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            emitted_at=emitted_at,
        )

    # -- Poll ---------------------------------------------------------------

    def poll(self, since: str | None = None) -> list[Event]:
        """Return all events emitted at or after `since`.

        Args:
            since: ISO-8601 UTC timestamp string (e.g. "2026-03-16T10:00:00Z").
                   If None, returns all events (use sparingly on large dirs).

        Returns:
            List of Events sorted oldest-first.
        """
        if since is not None and not isinstance(since, str):
            raise ValueError("since must be an ISO-8601 string or None")

        since_norm = _normalise_iso(since) if since else None
        events: list[Event] = []

        try:
            paths = sorted(self._events_dir.glob("*.json"))
        except OSError as exc:
            logger.error("poll: cannot list events dir: %s", exc)
            return []

        for path in paths:
            # Fast path: filename prefix is the timestamp — skip before parsing
            if since_norm and path.name[:19] < since_norm[:19].replace(":", "-"):
                continue

            event = _load_event_file(path)
            if event is None:
                continue

            if since_norm and event.emitted_at < since_norm:
                continue

            events.append(event)

        return events

    # -- Prune --------------------------------------------------------------

    def prune(self, older_than: str) -> int:
        """Delete event files older than `older_than` ISO timestamp.

        Returns count of files deleted.
        """
        if not isinstance(older_than, str):
            raise ValueError("older_than must be an ISO-8601 string")

        older_norm = _normalise_iso(older_than)
        deleted = 0
        for path in self._events_dir.glob("*.json"):
            event = _load_event_file(path)
            if event is None:
                continue
            if event.emitted_at < older_norm:
                try:
                    path.unlink()
                    deleted += 1
                except OSError as exc:
                    logger.warning("prune: could not delete %s: %s", path.name, exc)

        logger.info("prune: deleted %d event files older than %s", deleted, older_than)
        return deleted

    # -- Stats --------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return summary statistics for the events directory."""
        try:
            files = list(self._events_dir.glob("*.json"))
        except OSError:
            files = []

        type_counts: dict[str, int] = {}
        for path in files:
            # Extract event_type from filename: <ts>_<event_type>_<id8>.json
            parts = path.stem.split("_", 2)
            if len(parts) >= 3:
                # ts has form YYYY-MM-DDTHH-MM-SSZ — first two splits are date/time
                # reconstruct: stem = "2026-03-16T10-00-00Z_run_completed_abc12345"
                # split at first two underscores gives: ["2026-03-16T10-00-00Z", "run", ...]
                # so we need to handle multi-word types like "run_completed"
                # filename format: <iso_with_dashes>_<event_type>_<id8>.json
                # iso part: "2026-03-16T10-00-00Z" → index 0
                # last part: 8-char uuid prefix → split from right
                name_no_id = path.stem.rsplit("_", 1)[0]  # drop last _<id8>
                etype = name_no_id.split("_", 1)[-1]       # drop iso prefix
                type_counts[etype] = type_counts.get(etype, 0) + 1

        return {
            "total_events": len(files),
            "events_dir": str(self._events_dir),
            "by_type": type_counts,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalise_iso(ts: str) -> str:
    """Normalise timestamp to comparable string (strip Z, space → T)."""
    return ts.replace(" ", "T").rstrip("Z") + "Z" if not ts.endswith("Z") else ts


def _safe_filename(value: str) -> str:
    """Strip characters unsafe in filenames."""
    return "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in value)


def _load_event_file(path: Path) -> Event | None:
    """Parse one event JSON file. Returns None on any error."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Event(
            event_id=raw.get("event_id", ""),
            event_type=raw.get("event_type", ""),
            payload=raw.get("payload", {}),
            emitted_at=raw.get("emitted_at", ""),
        )
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("_load_event_file: could not read %s: %s", path.name, exc)
        return None


# ---------------------------------------------------------------------------
# Module-level singleton (optional convenience)
# ---------------------------------------------------------------------------

_default_bus: EventBus | None = None


def get_bus(events_dir: Path | str = DEFAULT_EVENTS_DIR) -> EventBus:
    """Return a module-level singleton EventBus (creates on first call)."""
    global _default_bus  # noqa: PLW0603
    if _default_bus is None:
        _default_bus = EventBus(events_dir)
    return _default_bus
