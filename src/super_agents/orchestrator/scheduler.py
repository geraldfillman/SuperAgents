"""scheduler.py

Cron-like scheduler for Super_Agents agent workflows.

Supports a simplified cron syntax:
  - ``*/N``  — every N minutes  (e.g. ``*/15`` = every 15 minutes)
  - ``@hourly`` / ``*/60`` — every hour
  - ``H:MM`` — daily at HH:MM (24-hour, e.g. ``06:30``)
  - 5-field cron strings (minute hour dom month dow) for forward-compatibility

Usage:
    sched = get_scheduler()
    sched.add("daily_biotech", "06:00", "biotech", "fda_tracker", "fetch_drug_approvals", args=["--days", "1"])
    sched.run()
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from super_agents.common.paths import DATA_DIR, ensure_directory
from super_agents.orchestrator.orchestrator import Orchestrator, get_orchestrator

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULES_PATH = DATA_DIR / "schedules.json"


# ---------------------------------------------------------------------------
# Schedule dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Schedule:
    """Immutable description of a scheduled agent task."""

    name: str
    cron_expr: str
    agent: str
    skill: str
    script: str
    args: tuple[str, ...]  # tuple so it stays hashable/frozen
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dict."""
        d = asdict(self)
        d["args"] = list(d["args"])  # tuple → list for JSON
        return d

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Schedule:
        """Deserialise from a JSON dict."""
        return Schedule(
            name=data["name"],
            cron_expr=data["cron_expr"],
            agent=data["agent"],
            skill=data["skill"],
            script=data["script"],
            args=tuple(data.get("args") or []),
            enabled=data.get("enabled", True),
        )


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Register, persist, and execute scheduled agent tasks."""

    def __init__(self, orchestrator: Orchestrator | None = None) -> None:
        self._orchestrator = orchestrator or get_orchestrator()
        self._schedules: dict[str, Schedule] = {}

    # -- Registration -------------------------------------------------------

    def add(
        self,
        name: str,
        cron_expr: str,
        agent: str,
        skill: str,
        script: str,
        *,
        args: list[str] | None = None,
    ) -> Schedule:
        """Register a new scheduled task.

        Args:
            name: Unique schedule identifier.
            cron_expr: Cron expression (e.g. ``*/15``, ``06:30``, ``0 6 * * *``).
            agent: Agent name.
            skill: Skill name.
            script: Script name (without .py).
            args: Optional extra CLI arguments.

        Returns:
            The registered (immutable) Schedule.
        """
        if not name:
            raise ValueError("Schedule name must not be empty")
        schedule = Schedule(
            name=name,
            cron_expr=cron_expr,
            agent=agent,
            skill=skill,
            script=script,
            args=tuple(args or []),
            enabled=True,
        )
        self._schedules = {**self._schedules, name: schedule}
        logger.info("Registered schedule %r: %s/%s @ %s", name, agent, skill, cron_expr)
        return schedule

    def remove(self, name: str) -> bool:
        """Unregister a schedule by name.

        Returns:
            True if removed, False if not found.
        """
        if name not in self._schedules:
            return False
        self._schedules = {k: v for k, v in self._schedules.items() if k != name}
        logger.info("Removed schedule %r", name)
        return True

    def list_schedules(self) -> list[Schedule]:
        """Return all registered schedules."""
        return list(self._schedules.values())

    # -- Due-check ----------------------------------------------------------

    def is_due(self, schedule: Schedule) -> bool:
        """Return True if the schedule's cron expression matches the current minute.

        Supported expressions:
          - ``*/N``        — every N minutes
          - ``H:MM``       — daily at HH:MM (matches exact minute)
          - 5-field cron   — ``minute hour dom month dow``  (partial: checks minute/hour only)
        """
        if not schedule.enabled:
            return False

        now = datetime.now(tz=timezone.utc)
        expr = schedule.cron_expr.strip()

        try:
            # Every-N-minutes: */N
            if expr.startswith("*/"):
                n = int(expr[2:])
                if n <= 0:
                    return False
                return now.minute % n == 0

            # Daily at HH:MM
            if ":" in expr and len(expr) <= 5:
                h_str, m_str = expr.split(":", 1)
                return now.hour == int(h_str) and now.minute == int(m_str)

            # 5-field cron string — check minute and hour fields only
            fields = expr.split()
            if len(fields) == 5:
                minute_field, hour_field = fields[0], fields[1]
                minute_ok = _cron_field_matches(minute_field, now.minute, 0, 59)
                hour_ok = _cron_field_matches(hour_field, now.hour, 0, 23)
                return minute_ok and hour_ok

        except (ValueError, ZeroDivisionError) as exc:
            logger.warning("is_due: invalid cron_expr %r for schedule %r: %s", expr, schedule.name, exc)

        return False

    # -- Tick / run loop ----------------------------------------------------

    def tick(self) -> list[str]:
        """Check all schedules and spawn any that are due.

        Returns:
            List of session names for newly spawned agents.
        """
        spawned: list[str] = []
        for schedule in self._schedules.values():
            if not self.is_due(schedule):
                continue
            logger.info("tick: schedule %r is due — spawning %s/%s", schedule.name, schedule.agent, schedule.skill)
            try:
                session = self._orchestrator.spawn_agent(
                    schedule.agent,
                    schedule.skill,
                    schedule.script,
                    args=list(schedule.args),
                )
                spawned.append(session)
            except RuntimeError as exc:
                logger.error("tick: failed to spawn %r: %s", schedule.name, exc)
        return spawned

    def run(self, *, check_interval: int = 60) -> None:
        """Blocking scheduler loop. Calls tick() every check_interval seconds.

        Runs until KeyboardInterrupt.
        """
        logger.info("Scheduler started (check_interval=%ds, %d schedules)", check_interval, len(self._schedules))
        try:
            while True:
                spawned = self.tick()
                if spawned:
                    logger.info("Scheduler spawned %d sessions: %s", len(spawned), spawned)
                time.sleep(check_interval)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")

    # -- Persistence --------------------------------------------------------

    def save_schedules(self, path: Path | None = None) -> None:
        """Persist schedules to JSON.

        Args:
            path: Target file path (defaults to data/schedules.json).
        """
        target = Path(path) if path else DEFAULT_SCHEDULES_PATH
        ensure_directory(target.parent)
        data = [s.to_dict() for s in self._schedules.values()]
        try:
            target.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("Saved %d schedules to %s", len(data), target)
        except OSError as exc:
            logger.error("save_schedules: could not write %s: %s", target, exc)
            raise

    def load_schedules(self, path: Path | None = None) -> None:
        """Load schedules from JSON, merging with any already registered.

        Args:
            path: Source file path (defaults to data/schedules.json).
        """
        source = Path(path) if path else DEFAULT_SCHEDULES_PATH
        if not source.exists():
            logger.debug("load_schedules: file not found: %s", source)
            return
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("load_schedules: could not read %s: %s", source, exc)
            return

        loaded = 0
        new_schedules = dict(self._schedules)
        for entry in raw:
            try:
                schedule = Schedule.from_dict(entry)
                new_schedules[schedule.name] = schedule
                loaded += 1
            except (KeyError, TypeError) as exc:
                logger.warning("load_schedules: skipping invalid entry %r: %s", entry, exc)
        self._schedules = new_schedules
        logger.info("Loaded %d schedules from %s", loaded, source)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cron_field_matches(field: str, value: int, min_val: int, max_val: int) -> bool:
    """Check if a single cron field matches a numeric value.

    Supports: ``*``, ``*/N``, and exact integers.
    """
    field = field.strip()
    if field == "*":
        return True
    if field.startswith("*/"):
        try:
            step = int(field[2:])
            return value % step == 0
        except ValueError:
            return False
    try:
        return int(field) == value
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_scheduler: Scheduler | None = None


def get_scheduler() -> Scheduler:
    """Return the module-level singleton Scheduler (creates on first call)."""
    global _default_scheduler  # noqa: PLW0603
    if _default_scheduler is None:
        _default_scheduler = Scheduler()
    return _default_scheduler
