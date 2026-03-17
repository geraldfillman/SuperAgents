"""super_agents.data — Unified data layer for the Super_Agents dashboard.

Public API:
    UnifiedStore   — SQLite WAL-mode store (all tables)
    DashboardDAL   — typed query layer with TTL caching
    EventBus       — file-based event bus

Convenience singletons (lazily initialised):
    get_store()    — module-level UnifiedStore instance
    get_dal()      — module-level DashboardDAL instance
    get_bus()      — module-level EventBus instance
"""

from __future__ import annotations

from super_agents.data.dal import (
    DashboardDAL,
    AgentDetail,
    AgentSummary,
    CalendarEvent,
    Finding,
    FleetSummary,
    LLMMetrics,
    RiskItem,
    RiskSummary,
    Run,
    Signal,
    get_dal,
)
from super_agents.data.events import Event, EventBus, get_bus
from super_agents.data.unified_store import UnifiedStore, get_store

__all__ = [
    # Store
    "UnifiedStore",
    "get_store",
    # DAL
    "DashboardDAL",
    "get_dal",
    "AgentDetail",
    "AgentSummary",
    "CalendarEvent",
    "Finding",
    "FleetSummary",
    "LLMMetrics",
    "RiskItem",
    "RiskSummary",
    "Run",
    "Signal",
    # Events
    "Event",
    "EventBus",
    "get_bus",
]
