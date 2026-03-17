"""dal.py

Dashboard Access Layer (DAL) — single entry point for all dashboard queries.

Design decisions:
- All return types are frozen dataclasses (immutable — never mutate).
- DAL-level dict-based cache with configurable TTL keeps raw SQLite off the
  Streamlit render path.
- No Streamlit imports — fully unit-testable.
- Errors are logged and surfaced as empty result sets, never raised to callers.

Usage:
    dal = DashboardDAL()
    summary = dal.fleet_summary()
    runs = dal.runs(sector="biotech", since="2026-03-01", limit=20)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from super_agents.common.paths import DATA_DIR
from super_agents.data.unified_store import UnifiedStore, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default cache TTLs (seconds)
# ---------------------------------------------------------------------------

DEFAULT_TTL: dict[str, int] = {
    "fleet_summary": 60,
    "agent_detail": 30,
    "runs": 30,
    "findings": 60,
    "signals": 30,
    "risk_summary": 120,
    "calendar_events": 300,
    "llm_metrics": 120,
}


# ---------------------------------------------------------------------------
# Return types — all frozen / immutable
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentSummary:
    name: str
    sector: str
    status: str
    last_run_at: str | None
    run_count: int
    skill_count: int
    last_error: str | None


@dataclass(frozen=True)
class FleetSummary:
    total_agents: int
    active_agents: int
    error_agents: int
    idle_agents: int
    total_runs: int
    total_findings: int
    total_signals: int
    agents: tuple[AgentSummary, ...]


@dataclass(frozen=True)
class AgentDetail:
    name: str
    sector: str
    status: str
    last_run_at: str | None
    run_count: int
    skill_count: int
    last_error: str | None
    recent_runs: tuple[dict[str, Any], ...]
    recent_findings: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class Run:
    run_id: str
    agent: str
    skill: str
    status: str
    started_at: str | None
    completed_at: str | None
    duration_sec: float | None
    record_count: int
    error: str | None
    sector: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class Finding:
    finding_id: str
    agent: str
    title: str
    summary: str
    severity: str
    finding_time: str
    source_url: str | None
    source_type: str | None
    confidence: str
    sector: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class Signal:
    signal_id: str
    source: str
    topic: str
    payload: dict[str, Any]
    timestamp: str
    confidence: str
    sectors: tuple[str, ...]
    processed: bool
    sector: str


@dataclass(frozen=True)
class RiskItem:
    category: str
    sector: str
    level: str
    count: int
    latest_finding_time: str | None


@dataclass(frozen=True)
class RiskSummary:
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    items: tuple[RiskItem, ...]


@dataclass(frozen=True)
class CalendarEvent:
    event_id: str
    agent: str
    event_type: str
    title: str
    event_date: str | None
    sector: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class LLMMetrics:
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost_usd: float
    model_breakdown: tuple[dict[str, Any], ...]
    agent_breakdown: tuple[dict[str, Any], ...]


# ---------------------------------------------------------------------------
# Cache entry
# ---------------------------------------------------------------------------

class _CacheEntry(NamedTuple):
    value: Any
    expires_at: float


# ---------------------------------------------------------------------------
# DashboardDAL
# ---------------------------------------------------------------------------

class DashboardDAL:
    """Single entry point for all dashboard data queries.

    Thread-safety: the underlying sqlite3 connection is opened with
    check_same_thread=False; for multi-threaded Streamlit use, create one
    DashboardDAL per thread or wrap calls in a lock.
    """

    def __init__(
        self,
        db_path: Path | str = DEFAULT_DB_PATH,
        ttl_overrides: dict[str, int] | None = None,
    ) -> None:
        self._store = UnifiedStore(db_path)
        self._conn: sqlite3.Connection = self._store._conn  # shared connection
        self._cache: dict[str, _CacheEntry] = {}
        self._ttl: dict[str, int] = {**DEFAULT_TTL, **(ttl_overrides or {})}

    # -- Lifecycle ----------------------------------------------------------

    def close(self) -> None:
        self._store.close()

    def __enter__(self) -> DashboardDAL:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def invalidate_cache(self, key: str | None = None) -> None:
        """Invalidate one cache key or the entire cache."""
        if key is None:
            self._cache.clear()
        else:
            self._cache.pop(key, None)

    # -- Fleet Summary ------------------------------------------------------

    def fleet_summary(self) -> FleetSummary:
        """Return a high-level snapshot of all agents."""
        cached = self._get_cached("fleet_summary")
        if cached is not None:
            return cached

        try:
            agents_rows = self._conn.execute(
                "SELECT * FROM agent_status ORDER BY last_run_at DESC"
            ).fetchall()
            runs_count = self._conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            findings_count = self._conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
            signals_count = self._conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]

            agents = tuple(
                AgentSummary(
                    name=row["agent"],
                    sector=row["sector"] or "",
                    status=row["status"] or "unknown",
                    last_run_at=row["last_run_at"],
                    run_count=row["run_count"] or 0,
                    skill_count=row["skill_count"] or 0,
                    last_error=row["last_error"],
                )
                for row in agents_rows
            )

            result = FleetSummary(
                total_agents=len(agents),
                active_agents=sum(1 for a in agents if a.status == "running"),
                error_agents=sum(1 for a in agents if a.status == "error"),
                idle_agents=sum(1 for a in agents if a.status not in ("running", "error")),
                total_runs=runs_count,
                total_findings=findings_count,
                total_signals=signals_count,
                agents=agents,
            )
        except sqlite3.Error as exc:
            logger.error("fleet_summary: DB error: %s", exc)
            result = FleetSummary(0, 0, 0, 0, 0, 0, 0, ())

        self._set_cached("fleet_summary", result)
        return result

    # -- Agent Detail -------------------------------------------------------

    def agent_detail(self, name: str) -> AgentDetail | None:
        """Return full detail for one agent, or None if not found."""
        if not name:
            raise ValueError("agent name must not be empty")

        cache_key = f"agent_detail:{name}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            row = self._conn.execute(
                "SELECT * FROM agent_status WHERE agent=?", (name,)
            ).fetchone()
            if row is None:
                return None

            recent_runs_rows = self._conn.execute(
                "SELECT * FROM runs WHERE agent=? ORDER BY started_at DESC LIMIT 10",
                (name,),
            ).fetchall()
            recent_findings_rows = self._conn.execute(
                "SELECT * FROM findings WHERE agent=? ORDER BY finding_time DESC LIMIT 10",
                (name,),
            ).fetchall()

            result = AgentDetail(
                name=row["agent"],
                sector=row["sector"] or "",
                status=row["status"] or "unknown",
                last_run_at=row["last_run_at"],
                run_count=row["run_count"] or 0,
                skill_count=row["skill_count"] or 0,
                last_error=row["last_error"],
                recent_runs=tuple(_row_to_run(r) for r in recent_runs_rows),
                recent_findings=tuple(_row_to_finding(r) for r in recent_findings_rows),
            )
        except sqlite3.Error as exc:
            logger.error("agent_detail(%s): DB error: %s", name, exc)
            return None

        self._set_cached(cache_key, result, ttl_key="agent_detail")
        return result

    # -- Runs ---------------------------------------------------------------

    def runs(
        self,
        sector: str | None = None,
        since: str | None = None,
        limit: int = 50,
    ) -> list[Run]:
        """Return agent runs, optionally filtered by sector and time."""
        if limit < 1 or limit > 10_000:
            raise ValueError(f"limit must be 1–10000, got {limit}")

        cache_key = f"runs:{sector}:{since}:{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            clauses: list[str] = []
            params: list[Any] = []
            if sector:
                clauses.append("sector=?")
                params.append(sector)
            if since:
                clauses.append("started_at >= ?")
                params.append(since)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(limit)
            rows = self._conn.execute(
                f"SELECT * FROM runs {where} ORDER BY started_at DESC LIMIT ?",
                params,
            ).fetchall()
            result = [_row_to_run(r) for r in rows]
        except sqlite3.Error as exc:
            logger.error("runs: DB error: %s", exc)
            result = []

        self._set_cached(cache_key, result, ttl_key="runs")
        return result

    # -- Findings -----------------------------------------------------------

    def findings(
        self,
        severity: str | None = None,
        sector: str | None = None,
        limit: int = 200,
    ) -> list[Finding]:
        """Return findings, optionally filtered by severity and sector."""
        cache_key = f"findings:{severity}:{sector}:{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            clauses: list[str] = []
            params: list[Any] = []
            if severity:
                clauses.append("severity=?")
                params.append(severity)
            if sector:
                clauses.append("sector=?")
                params.append(sector)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(limit)
            rows = self._conn.execute(
                f"SELECT * FROM findings {where} ORDER BY finding_time DESC LIMIT ?",
                params,
            ).fetchall()
            result = [_row_to_finding(r) for r in rows]
        except sqlite3.Error as exc:
            logger.error("findings: DB error: %s", exc)
            result = []

        self._set_cached(cache_key, result, ttl_key="findings")
        return result

    # -- Signals ------------------------------------------------------------

    def signals(
        self,
        topic: str | None = None,
        sector: str | None = None,
        limit: int = 200,
    ) -> list[Signal]:
        """Return signals, optionally filtered by topic prefix and sector."""
        cache_key = f"signals:{topic}:{sector}:{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            clauses: list[str] = []
            params: list[Any] = []
            if topic:
                clauses.append("topic LIKE ?")
                params.append(f"{topic}%")
            if sector:
                clauses.append("sector=?")
                params.append(sector)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(limit)
            rows = self._conn.execute(
                f"SELECT * FROM signals {where} ORDER BY timestamp DESC LIMIT ?",
                params,
            ).fetchall()
            result = [_row_to_signal(r) for r in rows]
        except sqlite3.Error as exc:
            logger.error("signals: DB error: %s", exc)
            result = []

        self._set_cached(cache_key, result, ttl_key="signals")
        return result

    # -- Risk Summary -------------------------------------------------------

    def risk_summary(self) -> RiskSummary:
        """Return aggregated risk counts grouped by severity."""
        cached = self._get_cached("risk_summary")
        if cached is not None:
            return cached

        try:
            rows = self._conn.execute(
                """
                SELECT severity, sector,
                       COUNT(*) AS cnt,
                       MAX(finding_time) AS latest
                FROM findings
                GROUP BY severity, sector
                ORDER BY finding_time DESC
                """
            ).fetchall()

            items = tuple(
                RiskItem(
                    category=row["severity"],
                    sector=row["sector"] or "",
                    level=row["severity"],
                    count=row["cnt"],
                    latest_finding_time=row["latest"],
                )
                for row in rows
            )

            def _count(level: str) -> int:
                return sum(i.count for i in items if i.level == level)

            result = RiskSummary(
                critical_count=_count("critical"),
                high_count=_count("high"),
                medium_count=_count("medium"),
                low_count=_count("low"),
                items=items,
            )
        except sqlite3.Error as exc:
            logger.error("risk_summary: DB error: %s", exc)
            result = RiskSummary(0, 0, 0, 0, ())

        self._set_cached("risk_summary", result)
        return result

    # -- Calendar Events ----------------------------------------------------

    def calendar_events(
        self,
        sector: str | None = None,
        month: str | None = None,
        limit: int = 500,
    ) -> list[CalendarEvent]:
        """Return calendar events, optionally filtered by sector and YYYY-MM month."""
        cache_key = f"calendar_events:{sector}:{month}:{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            clauses: list[str] = []
            params: list[Any] = []
            if sector:
                clauses.append("sector=?")
                params.append(sector)
            if month:
                clauses.append("event_date LIKE ?")
                params.append(f"{month}%")
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(limit)
            rows = self._conn.execute(
                f"SELECT * FROM events {where} ORDER BY event_date ASC LIMIT ?",
                params,
            ).fetchall()
            result = [_row_to_calendar_event(r) for r in rows]
        except sqlite3.Error as exc:
            logger.error("calendar_events: DB error: %s", exc)
            result = []

        self._set_cached(cache_key, result, ttl_key="calendar_events")
        return result

    # -- LLM Metrics --------------------------------------------------------

    def llm_metrics(self, since: str | None = None) -> LLMMetrics:
        """Return aggregated LLM token and cost metrics."""
        cache_key = f"llm_metrics:{since}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            where = "WHERE recorded_at >= ?" if since else ""
            params: list[Any] = [since] if since else []

            totals_row = self._conn.execute(
                f"""
                SELECT SUM(prompt_tokens) AS p,
                       SUM(completion_tokens) AS c,
                       SUM(total_tokens) AS t,
                       SUM(cost_usd) AS cost
                FROM metrics {where}
                """,
                params,
            ).fetchone()

            model_rows = self._conn.execute(
                f"""
                SELECT model,
                       SUM(prompt_tokens) AS p,
                       SUM(completion_tokens) AS c,
                       SUM(total_tokens) AS t,
                       SUM(cost_usd) AS cost,
                       COUNT(*) AS calls
                FROM metrics {where}
                GROUP BY model
                ORDER BY t DESC
                """,
                params,
            ).fetchall()

            agent_rows = self._conn.execute(
                f"""
                SELECT agent,
                       SUM(prompt_tokens) AS p,
                       SUM(completion_tokens) AS c,
                       SUM(total_tokens) AS t,
                       SUM(cost_usd) AS cost,
                       COUNT(*) AS calls
                FROM metrics {where}
                GROUP BY agent
                ORDER BY t DESC
                """,
                params,
            ).fetchall()

            result = LLMMetrics(
                total_prompt_tokens=int(totals_row["p"] or 0),
                total_completion_tokens=int(totals_row["c"] or 0),
                total_tokens=int(totals_row["t"] or 0),
                total_cost_usd=float(totals_row["cost"] or 0.0),
                model_breakdown=tuple(dict(r) for r in model_rows),
                agent_breakdown=tuple(dict(r) for r in agent_rows),
            )
        except sqlite3.Error as exc:
            logger.error("llm_metrics: DB error: %s", exc)
            result = LLMMetrics(0, 0, 0, 0.0, (), ())

        self._set_cached(cache_key, result, ttl_key="llm_metrics")
        return result

    # -- Cache internals ----------------------------------------------------

    def _get_cached(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._cache[key]
            return None
        return entry.value

    def _set_cached(
        self,
        key: str,
        value: Any,
        ttl_key: str | None = None,
    ) -> None:
        ttl = self._ttl.get(ttl_key or key, 60)
        self._cache[key] = _CacheEntry(value=value, expires_at=time.monotonic() + ttl)


# ---------------------------------------------------------------------------
# Row → dataclass converters (pure functions, no side effects)
# ---------------------------------------------------------------------------

def _parse_payload(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _row_to_run(row: sqlite3.Row) -> Run:
    return Run(
        run_id=row["run_id"],
        agent=row["agent"],
        skill=row["skill"] or "",
        status=row["status"] or "unknown",
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        duration_sec=row["duration_sec"],
        record_count=row["record_count"] or 0,
        error=row["error"],
        sector=row["sector"] or "",
        payload=_parse_payload(row["payload"]),
    )


def _row_to_finding(row: sqlite3.Row) -> Finding:
    return Finding(
        finding_id=row["finding_id"],
        agent=row["agent"],
        title=row["title"] or "",
        summary=row["summary"] or "",
        severity=row["severity"] or "info",
        finding_time=row["finding_time"],
        source_url=row["source_url"],
        source_type=row["source_type"],
        confidence=row["confidence"] or "secondary",
        sector=row["sector"] or "",
        payload=_parse_payload(row["payload"]),
    )


def _row_to_signal(row: sqlite3.Row) -> Signal:
    sectors_raw = row["sectors"] or "[]"
    try:
        sectors = tuple(json.loads(sectors_raw))
    except (json.JSONDecodeError, TypeError):
        sectors = ()
    return Signal(
        signal_id=row["signal_id"],
        source=row["source"],
        topic=row["topic"],
        payload=_parse_payload(row["payload"]),
        timestamp=row["timestamp"],
        confidence=row["confidence"] or "secondary",
        sectors=sectors,
        processed=bool(row["processed"]),
        sector=row["sector"] or "",
    )


def _row_to_calendar_event(row: sqlite3.Row) -> CalendarEvent:
    return CalendarEvent(
        event_id=row["event_id"],
        agent=row["agent"] or "",
        event_type=row["event_type"] or "",
        title=row["title"] or "",
        event_date=row["event_date"],
        sector=row["sector"] or "",
        payload=_parse_payload(row["payload"]),
    )


# ---------------------------------------------------------------------------
# Module-level singleton (optional convenience)
# ---------------------------------------------------------------------------

_default_dal: DashboardDAL | None = None


def get_dal(db_path: Path | str = DEFAULT_DB_PATH) -> DashboardDAL:
    """Return a module-level singleton DashboardDAL (creates on first call)."""
    global _default_dal  # noqa: PLW0603
    if _default_dal is None:
        _default_dal = DashboardDAL(db_path)
    return _default_dal
