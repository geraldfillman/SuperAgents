"""Signal Store — SQLite-backed storage for replay, audit, and simulation input.

Every signal that flows through the system gets persisted here.
This enables:
  - Replay: re-run signals through agents for testing
  - Audit: trace which signals triggered which agent actions
  - Simulation: use historical signals as scenario inputs
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from super_agents.common.data_result import Signal
from super_agents.common.paths import DATA_DIR, ensure_directory

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = DATA_DIR / "signals" / "signal_store.db"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS signals (
    signal_id   TEXT PRIMARY KEY,
    source      TEXT NOT NULL,
    topic       TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '{}',
    timestamp   TEXT NOT NULL,
    confidence  TEXT NOT NULL DEFAULT 'secondary',
    sectors     TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),

    -- Routing metadata (filled after routing)
    routed_to   TEXT DEFAULT NULL,
    processed   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_signals_topic ON signals(topic);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_processed ON signals(processed);
"""


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class SignalStore:
    """SQLite-backed signal persistence.

    Usage:
        store = SignalStore()
        store.save(signals)
        recent = store.query(topic="escalation.*", limit=50)
        replay = store.signals_for_replay(since="2026-03-15")
    """

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        ensure_directory(self._db_path.parent)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_CREATE_TABLE)

    def save(self, signals: list[Signal]) -> int:
        """Persist a batch of signals. Returns count of new signals saved."""
        saved = 0
        for signal in signals:
            try:
                self._conn.execute(
                    """INSERT OR IGNORE INTO signals
                       (signal_id, source, topic, payload, timestamp, confidence, sectors)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        signal.signal_id,
                        signal.source,
                        signal.topic,
                        json.dumps(signal.payload, default=str),
                        signal.timestamp.isoformat(),
                        signal.confidence,
                        json.dumps(list(signal.sectors)),
                    ),
                )
                saved += self._conn.total_changes  # approximate
            except sqlite3.Error as exc:
                logger.warning("Failed to save signal %s: %s", signal.signal_id, exc)

        self._conn.commit()
        logger.info("Saved %d signals to store", saved)
        return saved

    def mark_routed(self, signal_id: str, agents: list[str]) -> None:
        """Record which agents a signal was routed to."""
        self._conn.execute(
            "UPDATE signals SET routed_to = ? WHERE signal_id = ?",
            (json.dumps(agents), signal_id),
        )
        self._conn.commit()

    def mark_processed(self, signal_id: str) -> None:
        """Mark a signal as fully processed."""
        self._conn.execute(
            "UPDATE signals SET processed = 1 WHERE signal_id = ?",
            (signal_id,),
        )
        self._conn.commit()

    # -- Query API ----------------------------------------------------------

    def query(
        self,
        *,
        topic: str | None = None,
        source: str | None = None,
        since: str | None = None,
        until: str | None = None,
        sector: str | None = None,
        processed: bool | None = None,
        limit: int = 100,
    ) -> list[Signal]:
        """Query signals with optional filters.

        Args:
            topic: Filter by topic (supports SQL LIKE with %).
            source: Filter by source name.
            since: ISO timestamp — signals after this time.
            until: ISO timestamp — signals before this time.
            sector: Filter by sector (searches sectors JSON array).
            processed: Filter by processed state.
            limit: Maximum results.

        Returns:
            List of Signal objects matching the criteria.
        """
        clauses: list[str] = []
        params: list[Any] = []

        if topic:
            clauses.append("topic LIKE ?")
            params.append(topic.replace("*", "%"))
        if source:
            clauses.append("source LIKE ?")
            params.append(source.replace("*", "%"))
        if since:
            clauses.append("timestamp >= ?")
            params.append(since)
        if until:
            clauses.append("timestamp <= ?")
            params.append(until)
        if sector:
            clauses.append("(sectors LIKE ? OR sectors = '[]')")
            params.append(f'%"{sector}"%')
        if processed is not None:
            clauses.append("processed = ?")
            params.append(1 if processed else 0)

        where = " AND ".join(clauses) if clauses else "1=1"
        sql = f"SELECT * FROM signals WHERE {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_signal(row) for row in rows]

    def signals_for_replay(
        self,
        since: str | None = None,
        sectors: list[str] | None = None,
    ) -> list[Signal]:
        """Get signals suitable for replay (simulation input).

        Args:
            since: ISO timestamp — replay signals from this point.
            sectors: Only signals relevant to these sectors.

        Returns:
            Chronologically ordered signals for replay.
        """
        signals = self.query(since=since, limit=10000)

        if sectors:
            signals = [
                s for s in signals
                if not s.sectors or any(sec in s.sectors for sec in sectors)
            ]

        # Return in chronological order (oldest first)
        return list(reversed(signals))

    def count(self, **kwargs: Any) -> int:
        """Count signals matching filters."""
        return len(self.query(**kwargs))

    def stats(self) -> dict[str, Any]:
        """Return summary statistics about the signal store."""
        total = self._conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        processed = self._conn.execute("SELECT COUNT(*) FROM signals WHERE processed=1").fetchone()[0]
        sources = self._conn.execute("SELECT DISTINCT source FROM signals").fetchall()
        topics = self._conn.execute(
            "SELECT topic, COUNT(*) as cnt FROM signals GROUP BY topic ORDER BY cnt DESC LIMIT 20"
        ).fetchall()

        return {
            "total_signals": total,
            "processed": processed,
            "unprocessed": total - processed,
            "unique_sources": [r[0] for r in sources],
            "top_topics": {r["topic"]: r["cnt"] for r in topics},
            "db_path": str(self._db_path),
        }

    # -- Lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> SignalStore:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # -- Internal -----------------------------------------------------------

    @staticmethod
    def _row_to_signal(row: sqlite3.Row) -> Signal:
        """Convert a database row back to a Signal object."""
        return Signal(
            signal_id=row["signal_id"],
            source=row["source"],
            topic=row["topic"],
            payload=json.loads(row["payload"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            confidence=row["confidence"],
            sectors=tuple(json.loads(row["sectors"])),
        )
