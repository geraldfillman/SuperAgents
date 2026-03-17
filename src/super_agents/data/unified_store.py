"""unified_store.py

Single SQLite WAL-mode database for all Super_Agents dashboard data.

Replaces the scattered JSON files and standalone signal_store.db with one
authoritative database at data/super_agents.db.  Every table carries
`created_at`, `updated_at`, and `sector` columns so pages can filter
universally without joins.

Usage:
    store = UnifiedStore()
    store.save_signals(signals)
    store.save_run(run_dict)
    store.save_findings(findings_list)
    store.close()

    # or as context manager
    with UnifiedStore() as store:
        store.save_run(run)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from super_agents.common.data_result import Signal
from super_agents.common.paths import DATA_DIR, ensure_directory

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = DATA_DIR / "super_agents.db"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _json_dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError) as exc:
        logger.warning("json serialisation fallback: %s", exc)
        return "{}"


def _load_migration(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# UnifiedStore
# ---------------------------------------------------------------------------

class UnifiedStore:
    """SQLite-backed unified persistence for the Super_Agents dashboard.

    All methods return counts or dicts — they never mutate input objects.
    """

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        ensure_directory(self._db_path.parent)
        self._conn = self._connect()
        self._apply_migrations()

    # -- Lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        try:
            self._conn.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error closing UnifiedStore: %s", exc)

    def __enter__(self) -> UnifiedStore:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # -- Signals ------------------------------------------------------------

    def save_signals(self, signals: list[Signal]) -> int:
        """Persist a batch of Signal objects. Returns count of new rows saved."""
        if not signals:
            return 0

        saved = 0
        now = _now_iso()
        for signal in signals:
            if not isinstance(signal, Signal):
                logger.warning("save_signals: skipping non-Signal item %r", type(signal))
                continue
            try:
                sector = _first_sector(signal.sectors)
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO signals
                        (signal_id, source, topic, payload, timestamp,
                         confidence, sectors, processed, sector, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                    """,
                    (
                        signal.signal_id,
                        signal.source,
                        signal.topic,
                        _json_dumps(signal.payload),
                        signal.timestamp,
                        signal.confidence,
                        _json_dumps(list(signal.sectors)),
                        sector,
                        now,
                        now,
                    ),
                )
                if self._conn.execute(
                    "SELECT changes()"
                ).fetchone()[0]:
                    saved += 1
            except sqlite3.Error as exc:
                logger.error("save_signals: DB error for %s: %s", signal.signal_id, exc)

        self._conn.commit()
        return saved

    def save_signal_dict(self, signal_dict: dict[str, Any]) -> bool:
        """Persist a raw signal dict. Returns True if a new row was inserted."""
        _validate_dict(signal_dict, required_keys=("signal_id", "source", "topic"))
        now = _now_iso()
        signal_id = signal_dict["signal_id"]
        sectors_raw = signal_dict.get("sectors", [])
        sector = _first_sector(sectors_raw)
        try:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO signals
                    (signal_id, source, topic, payload, timestamp,
                     confidence, sectors, processed, sector, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_dict["source"],
                    signal_dict["topic"],
                    _json_dumps(signal_dict.get("payload", {})),
                    signal_dict.get("timestamp", now),
                    signal_dict.get("confidence", "secondary"),
                    _json_dumps(list(sectors_raw) if not isinstance(sectors_raw, str) else sectors_raw),
                    int(signal_dict.get("processed", 0)),
                    sector,
                    now,
                    now,
                ),
            )
            self._conn.commit()
            return bool(self._conn.execute("SELECT changes()").fetchone()[0])
        except sqlite3.Error as exc:
            logger.error("save_signal_dict: DB error for %s: %s", signal_id, exc)
            return False

    def mark_signals_processed(self, signal_ids: list[str]) -> int:
        """Mark signals as processed. Returns count updated."""
        if not signal_ids:
            return 0
        now = _now_iso()
        placeholders = ",".join("?" * len(signal_ids))
        self._conn.execute(
            f"UPDATE signals SET processed=1, updated_at=? WHERE signal_id IN ({placeholders})",
            [now, *signal_ids],
        )
        self._conn.commit()
        return self._conn.execute("SELECT changes()").fetchone()[0]

    # -- Runs ---------------------------------------------------------------

    def save_run(self, run: dict[str, Any]) -> bool:
        """Persist one agent run summary dict. Returns True if inserted."""
        _validate_dict(run, required_keys=("run_id", "agent"))
        now = _now_iso()
        run_id = run["run_id"]
        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO runs
                    (run_id, agent, skill, status, started_at, completed_at,
                     duration_sec, record_count, error, payload, sector,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    run["agent"],
                    run.get("skill", ""),
                    run.get("status", "unknown"),
                    run.get("started_at"),
                    run.get("completed_at"),
                    run.get("duration_seconds") or run.get("duration_sec"),
                    run.get("record_count", 0),
                    run.get("error"),
                    _json_dumps({k: v for k, v in run.items() if k not in _RUN_CORE_KEYS}),
                    run.get("sector", ""),
                    now,
                    now,
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.Error as exc:
            logger.error("save_run: DB error for %s: %s", run_id, exc)
            return False

    # -- Findings -----------------------------------------------------------

    def save_findings(self, findings: list[dict[str, Any]]) -> int:
        """Persist a list of finding dicts. Returns count of rows upserted."""
        if not findings:
            return 0
        saved = 0
        now = _now_iso()
        for finding in findings:
            if not isinstance(finding, dict):
                logger.warning("save_findings: skipping non-dict item")
                continue
            finding_id = finding.get("finding_id") or str(uuid.uuid4())
            try:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO findings
                        (finding_id, agent, title, summary, severity,
                         finding_time, source_url, source_type, confidence,
                         payload, sector, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        finding_id,
                        finding.get("agent", ""),
                        finding.get("title", ""),
                        finding.get("summary", ""),
                        finding.get("severity", "info"),
                        finding.get("finding_time", now),
                        finding.get("source_url"),
                        finding.get("source_type"),
                        finding.get("confidence", "secondary"),
                        _json_dumps({k: v for k, v in finding.items() if k not in _FINDING_CORE_KEYS}),
                        finding.get("sector", ""),
                        now,
                        now,
                    ),
                )
                saved += 1
            except sqlite3.Error as exc:
                logger.error("save_findings: DB error for %s: %s", finding_id, exc)

        self._conn.commit()
        return saved

    # -- Events -------------------------------------------------------------

    def save_event(self, event: dict[str, Any]) -> bool:
        """Persist one calendar/catalyst event. Returns True if inserted."""
        _validate_dict(event, required_keys=("event_id",))
        now = _now_iso()
        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO events
                    (event_id, agent, event_type, title, event_date,
                     payload, sector, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["event_id"],
                    event.get("agent", ""),
                    event.get("event_type", ""),
                    event.get("title", ""),
                    event.get("event_date"),
                    _json_dumps({k: v for k, v in event.items() if k not in _EVENT_CORE_KEYS}),
                    event.get("sector", ""),
                    now,
                    now,
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.Error as exc:
            logger.error("save_event: DB error for %s: %s", event.get("event_id"), exc)
            return False

    # -- Metrics ------------------------------------------------------------

    def save_metric(self, metric: dict[str, Any]) -> bool:
        """Persist one LLM usage metric record. Returns True if inserted."""
        now = _now_iso()
        metric_id = metric.get("metric_id") or str(uuid.uuid4())
        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO metrics
                    (metric_id, agent, model, prompt_tokens, completion_tokens,
                     total_tokens, cost_usd, run_id, recorded_at,
                     payload, sector, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metric_id,
                    metric.get("agent", ""),
                    metric.get("model", ""),
                    metric.get("prompt_tokens", 0),
                    metric.get("completion_tokens", 0),
                    metric.get("total_tokens", 0),
                    metric.get("cost_usd", 0.0),
                    metric.get("run_id"),
                    metric.get("recorded_at", now),
                    _json_dumps({k: v for k, v in metric.items() if k not in _METRIC_CORE_KEYS}),
                    metric.get("sector", ""),
                    now,
                    now,
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.Error as exc:
            logger.error("save_metric: DB error for %s: %s", metric_id, exc)
            return False

    # -- Agent status -------------------------------------------------------

    def upsert_agent_status(self, agent: str, status: dict[str, Any]) -> bool:
        """Update last-known agent state. Returns True on success."""
        if not agent:
            raise ValueError("agent name must not be empty")
        now = _now_iso()
        try:
            self._conn.execute(
                """
                INSERT INTO agent_status
                    (agent, status, last_run_id, last_run_at, last_error,
                     skill_count, run_count, payload, sector, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent) DO UPDATE SET
                    status=excluded.status,
                    last_run_id=excluded.last_run_id,
                    last_run_at=excluded.last_run_at,
                    last_error=excluded.last_error,
                    skill_count=excluded.skill_count,
                    run_count=excluded.run_count,
                    payload=excluded.payload,
                    sector=excluded.sector,
                    updated_at=excluded.updated_at
                """,
                (
                    agent,
                    status.get("status", "unknown"),
                    status.get("last_run_id"),
                    status.get("last_run_at"),
                    status.get("last_error"),
                    status.get("skill_count", 0),
                    status.get("run_count", 0),
                    _json_dumps({k: v for k, v in status.items() if k not in _AGENT_STATUS_CORE_KEYS}),
                    status.get("sector", ""),
                    now,
                    now,
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.Error as exc:
            logger.error("upsert_agent_status: DB error for %s: %s", agent, exc)
            return False

    # -- Stats --------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return row counts for all tables."""
        tables = ("signals", "runs", "findings", "events", "metrics", "agent_status")
        counts: dict[str, Any] = {}
        for table in tables:
            row = self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            counts[table] = row[0] if row else 0
        counts["db_path"] = str(self._db_path)
        return counts

    # -- Internal -----------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _apply_migrations(self) -> None:
        """Run any unapplied SQL migration files in order."""
        # Bootstrap schema_migrations table if it doesn't exist yet
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version    TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        self._conn.commit()

        applied: set[str] = {
            row[0]
            for row in self._conn.execute("SELECT version FROM schema_migrations").fetchall()
        }

        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for migration_path in migration_files:
            version = migration_path.stem
            if version in applied:
                continue
            logger.info("Applying migration: %s", version)
            sql = _load_migration(migration_path)
            try:
                self._conn.executescript(sql)
                self._conn.commit()
                logger.info("Migration %s applied.", version)
            except sqlite3.Error as exc:
                logger.error("Migration %s FAILED: %s", version, exc)
                raise


# ---------------------------------------------------------------------------
# Column key sets (used when building payload blobs)
# ---------------------------------------------------------------------------

_RUN_CORE_KEYS = frozenset(
    {"run_id", "agent", "skill", "status", "started_at", "completed_at",
     "duration_seconds", "duration_sec", "record_count", "error", "sector"}
)

_FINDING_CORE_KEYS = frozenset(
    {"finding_id", "agent", "title", "summary", "severity", "finding_time",
     "source_url", "source_type", "confidence", "sector"}
)

_EVENT_CORE_KEYS = frozenset(
    {"event_id", "agent", "event_type", "title", "event_date", "sector"}
)

_METRIC_CORE_KEYS = frozenset(
    {"metric_id", "agent", "model", "prompt_tokens", "completion_tokens",
     "total_tokens", "cost_usd", "run_id", "recorded_at", "sector"}
)

_AGENT_STATUS_CORE_KEYS = frozenset(
    {"agent", "status", "last_run_id", "last_run_at", "last_error",
     "skill_count", "run_count", "sector"}
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_sector(sectors: Any) -> str:
    """Extract the first sector string from a list or string value."""
    if isinstance(sectors, str):
        return sectors
    if isinstance(sectors, (list, tuple)) and sectors:
        return str(sectors[0])
    return ""


def _validate_dict(data: dict[str, Any], required_keys: tuple[str, ...]) -> None:
    """Raise ValueError if required keys are missing."""
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"Missing required keys: {missing}")


# ---------------------------------------------------------------------------
# Module-level singleton (optional convenience)
# ---------------------------------------------------------------------------

_default_store: UnifiedStore | None = None


def get_store(db_path: Path | str = DEFAULT_DB_PATH) -> UnifiedStore:
    """Return a module-level singleton UnifiedStore (creates on first call)."""
    global _default_store  # noqa: PLW0603
    if _default_store is None:
        _default_store = UnifiedStore(db_path)
    return _default_store
