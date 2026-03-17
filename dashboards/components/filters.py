"""Global filter bar component — persists filters in st.session_state."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import streamlit as st

from dashboards.dashboard_data import AGENT_SECTOR_MAP, discover_agent_names

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_SEVERITY_OPTIONS = ["critical", "high", "medium", "low", "info"]
_TIME_PRESETS = ["24h", "7d", "30d", "90d", "custom"]

_DEFAULTS: dict[str, Any] = {
    "filter_sectors": [],
    "filter_time_preset": "7d",
    "filter_time_start": None,
    "filter_time_end": None,
    "filter_severities": [],
    "filter_agents": [],
}


def _init_session_state() -> None:
    """Initialise filter keys in session_state if not already set."""
    for key, default in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _preset_to_since(preset: str) -> datetime:
    """Return a UTC datetime for the given preset label."""
    now = datetime.utcnow()
    mapping = {
        "24h": now - timedelta(hours=24),
        "7d": now - timedelta(days=7),
        "30d": now - timedelta(days=30),
        "90d": now - timedelta(days=90),
    }
    return mapping.get(preset, now - timedelta(days=7))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_filters(*, show_agent_filter: bool = True) -> None:
    """Render the global filter sidebar. Call once per page before main content."""
    _init_session_state()

    st.sidebar.header("Filters")

    # --- Sector ---
    sector_options = list(AGENT_SECTOR_MAP.keys())
    st.session_state["filter_sectors"] = st.sidebar.multiselect(
        "Sector",
        options=sector_options,
        default=st.session_state["filter_sectors"],
        format_func=lambda s: f"{AGENT_SECTOR_MAP[s]['icon']} {s.replace('_', ' ').title()}",
        key="_sidebar_sectors",
    )

    # --- Time range ---
    st.sidebar.markdown("**Time Range**")
    preset = st.sidebar.radio(
        "Preset",
        options=_TIME_PRESETS,
        index=_TIME_PRESETS.index(st.session_state["filter_time_preset"]),
        horizontal=True,
        key="_sidebar_time_preset",
        label_visibility="collapsed",
    )
    st.session_state["filter_time_preset"] = preset

    if preset == "custom":
        col_a, col_b = st.sidebar.columns(2)
        default_start = st.session_state["filter_time_start"] or (
            datetime.utcnow() - timedelta(days=7)
        ).date()
        default_end = st.session_state["filter_time_end"] or datetime.utcnow().date()
        st.session_state["filter_time_start"] = col_a.date_input(
            "From", value=default_start, key="_sidebar_date_start"
        )
        st.session_state["filter_time_end"] = col_b.date_input(
            "To", value=default_end, key="_sidebar_date_end"
        )

    # --- Severity ---
    st.session_state["filter_severities"] = st.sidebar.multiselect(
        "Severity",
        options=_SEVERITY_OPTIONS,
        default=st.session_state["filter_severities"],
        key="_sidebar_severities",
    )

    # --- Agent ---
    if show_agent_filter:
        agent_names = discover_agent_names()
        st.session_state["filter_agents"] = st.sidebar.multiselect(
            "Agent",
            options=agent_names,
            default=[a for a in st.session_state["filter_agents"] if a in agent_names],
            format_func=lambda a: a.replace("_", " ").title(),
            key="_sidebar_agents",
        )

    # --- Reset ---
    if st.sidebar.button("Reset Filters", use_container_width=True):
        for key, default in _DEFAULTS.items():
            st.session_state[key] = default
        st.rerun()


def get_active_filters() -> dict[str, Any]:
    """Return the current filter state as a plain dict for passing to data functions."""
    _init_session_state()

    preset = st.session_state["filter_time_preset"]
    if preset == "custom":
        time_start = st.session_state.get("filter_time_start")
        time_end = st.session_state.get("filter_time_end")
        since = datetime.combine(time_start, datetime.min.time()) if time_start else None
        until = datetime.combine(time_end, datetime.max.time()) if time_end else None
    else:
        since = _preset_to_since(preset)
        until = None

    return {
        "sectors": list(st.session_state["filter_sectors"]),
        "severities": list(st.session_state["filter_severities"]),
        "agents": list(st.session_state["filter_agents"]),
        "time_preset": preset,
        "since": since,
        "until": until,
    }


def apply_finding_filters(
    findings: list[dict[str, Any]],
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Filter a findings list using the active (or provided) filter state."""
    if filters is None:
        filters = get_active_filters()

    result = list(findings)

    if filters["sectors"]:
        result = [
            f for f in result
            if f.get("sector") in filters["sectors"]
            or f.get("_agent") in filters["sectors"]
        ]

    if filters["severities"]:
        result = [
            f for f in result
            if f.get("severity", "").lower() in filters["severities"]
        ]

    if filters["agents"]:
        result = [
            f for f in result
            if f.get("_agent") in filters["agents"]
        ]

    if filters.get("since"):
        since_str = filters["since"].isoformat()
        result = [
            f for f in result
            if f.get("finding_time", "") >= since_str
        ]

    return result
