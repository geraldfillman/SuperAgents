"""Centralized theme, constants, and UI helpers for the dashboard."""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

DASHBOARD_VERSION = "0.3.0"

# ---------------------------------------------------------------------------
# Severity constants (single source of truth for all pages)
# ---------------------------------------------------------------------------

SEVERITY_ICONS: dict[str, str] = {
    "critical": "\U0001f6d1",  # red octagon
    "high": "\U0001f7e0",      # orange circle
    "medium": "\U0001f7e1",    # yellow circle
    "low": "\U0001f535",       # blue circle
    "info": "\u26aa",          # white circle
}

SEVERITY_COLORS: dict[str, str] = {
    "critical": "#E74C3C",
    "high": "#E67E22",
    "medium": "#F1C40F",
    "low": "#3498DB",
    "info": "#95A5A6",
}

STATUS_ICONS: dict[str, str] = {
    "running": "\U0001f7e2",   # green circle
    "completed": "\U0001f535", # blue circle
    "failed": "\U0001f534",    # red circle
    "idle": "\u26aa",          # white circle
}

# ---------------------------------------------------------------------------
# Sector metadata (imported from dashboard_data to keep one map)
# ---------------------------------------------------------------------------

# Re-export from dashboard_data so pages can do:
#   from dashboards.components.theme import get_sector_metadata
from dashboards.dashboard_data import get_agent_sector as get_sector_metadata  # noqa: F401


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

def setup_page(page_title: str, page_icon: str = "\U0001f52c") -> None:
    """Standard page configuration, CSS injection, and sidebar footer."""
    st.set_page_config(
        page_title=f"{page_title} | Super Agents",
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_css()
    # Sidebar footer
    st.sidebar.divider()
    st.sidebar.caption(f"Super Agents v{DASHBOARD_VERSION}")


def get_severity_icon(severity: str) -> str:
    """Return the emoji icon for a finding severity level."""
    return SEVERITY_ICONS.get(severity.lower(), SEVERITY_ICONS["info"])


def get_severity_color(severity: str) -> str:
    """Return the hex color for a finding severity level."""
    return SEVERITY_COLORS.get(severity.lower(), SEVERITY_COLORS["info"])


def get_status_icon(status: str) -> str:
    """Return the emoji icon for an agent/run status."""
    return STATUS_ICONS.get(status.lower(), STATUS_ICONS["idle"])


# ---------------------------------------------------------------------------
# Navigation group constants (Phase 3.1)
# ---------------------------------------------------------------------------

NAV_GROUPS: dict[str, list[str]] = {
    "Monitoring": [
        "Fleet Overview",
        "Agent Detail",
        "Run History",
    ],
    "Intelligence": [
        "Findings Board",
        "Signal Explorer",
        "Risk Dashboard",
    ],
    "Simulations": [
        "Scenario Builder",
        "MiroFish Bundles",
    ],
    "Operations": [
        "Cybersecurity",
        "LLM Metrics",
    ],
    "Settings": [
        "Settings",
    ],
}

# Page file mapping (label → page filename stem)
NAV_PAGE_FILES: dict[str, str] = {
    "Fleet Overview": "01_Fleet_Overview",
    "Agent Detail": "02_Agent_Detail",
    "Run History": "03_Run_History",
    "Findings Board": "04_Findings_Board",
    "Signal Explorer": "05_Signal_Explorer",
    "Risk Dashboard": "06_Risk_Dashboard",
    "Calendars": "07_Calendars",
    "Scenario Builder": "08_Simulations",
    "MiroFish Bundles": "08_Simulations",
    "Cybersecurity": "09_Cybersecurity",
    "LLM Metrics": "10_LLM_Metrics",
    "Settings": "11_Settings",
}


# ---------------------------------------------------------------------------
# apply_custom_css kept for backward compat but now a no-op (CSS in setup_page)
# ---------------------------------------------------------------------------

def apply_custom_css() -> None:  # noqa: D401
    """No-op kept for backward compatibility. CSS is injected via setup_page()."""


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        /* Metric cards */
        .stMetric {
            background-color: rgba(255, 255, 255, 0.05);
            padding: 10px;
            border-radius: 5px;
        }
        /* Tighter expander spacing */
        .streamlit-expanderHeader { font-size: 0.95rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
