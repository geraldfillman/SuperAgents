"""Settings — System health, configurations, and cache management."""

from __future__ import annotations

import sys

import streamlit as st

from dashboards.dashboard_data import (
    PROJECT_ROOT,
    CRUCIX_SIGNALS_DB,
    detect_mirofish_services,
    discover_runnable_agents,
    load_crucix_signal_stats,
    load_crucix_status,
)
from dashboards.components.theme import DASHBOARD_VERSION, setup_page, apply_custom_css

setup_page("Settings", "\u2699\ufe0f")
apply_custom_css()

st.header("System Settings")
st.caption(f"Dashboard v{DASHBOARD_VERSION}")

tab1, tab2, tab3 = st.tabs(["Health & Config", "CLI Cheatsheet", "Cache Management"])

# ---------------------------------------------------------------------------
# Tab 1 — Health
# ---------------------------------------------------------------------------

with tab1:
    st.subheader("System Health")
    crucix = load_crucix_status()
    agents = discover_runnable_agents()
    signal_stats = load_crucix_signal_stats()
    mirofish = detect_mirofish_services()

    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown("**Core Components**")
        st.write(f"- Crucix: {'\u2705 Installed' if crucix['installed'] else '\u274c Missing'}")
        st.write(f"- Signal DB: {'\u2705 Active' if crucix['signals_db_exists'] else '\u274c Missing'}")
        st.write(f"- Signals stored: {signal_stats.get('total_signals', 0)}")
        st.write(f"- Agents discovered: {len(agents)}")

    with h2:
        st.markdown("**MiroFish Services**")
        st.write(f"- Frontend: {'\u2705 Up' if mirofish['frontend_reachable'] else '\u274c Down'}")
        st.write(f"- Backend: {'\u2705 Up' if mirofish['backend_reachable'] else '\u274c Down'}")
        st.write(f"- Runtime home: {'\u2705' if mirofish['runtime_home_exists'] else '\u274c'}")

    with h3:
        st.markdown("**Environment**")
        st.write(f"- Python: {sys.version.split()[0]}")
        st.write(f"- Project root: `{PROJECT_ROOT}`")
        st.write(f"- Signals DB: `{CRUCIX_SIGNALS_DB}`")

    st.divider()
    st.subheader("Agent Configuration Status")
    agent_rows = [
        {
            "Agent": a["label"],
            "Config": "\u2705" if a["config_exists"] else "\u274c",
            "Skills": a["skill_count"],
            "Scripts": a["script_count"],
            "Workflows": a["workflow_count"],
        }
        for a in agents
    ]
    if agent_rows:
        st.dataframe(agent_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No agents discovered.")

# ---------------------------------------------------------------------------
# Tab 2 — CLI Cheatsheet
# ---------------------------------------------------------------------------

with tab2:
    st.subheader("CLI Commands")

    st.markdown("### \U0001f3c3 Running Agents")
    st.code(
        "python -m super_agents list\n"
        "python -m super_agents list --agent biotech\n"
        "python -m super_agents run --agent biotech --verbose\n"
        "python -m super_agents search --verbose",
        language="bash",
    )

    st.markdown("### \U0001f4e1 Crucix Operations")
    st.code(
        "python -m super_agents crucix status\n"
        "python -m super_agents crucix setup\n"
        "python -m super_agents crucix sweep --store\n"
        "python -m super_agents crucix signals --topic maritime",
        language="bash",
    )

    st.markdown("### \U0001f3ad Simulations")
    st.code(
        "python -m super_agents simulate scenarios/hormuz_zero_transit.yaml\n"
        "python -m super_agents simulate scenarios/hormuz_zero_transit.yaml --json-only",
        language="bash",
    )

    st.markdown("### \U0001f4ca Dashboard")
    st.code(
        "streamlit run dashboards/app.py",
        language="bash",
    )

# ---------------------------------------------------------------------------
# Tab 3 — Cache Management
# ---------------------------------------------------------------------------

with tab3:
    st.subheader("Cache Management")
    st.write(
        "The dashboard uses `@st.cache_data` with a **5-minute TTL** for filesystem scans. "
        "Press the button below to force a fresh reload."
    )

    if st.button("Clear Dashboard Cache", type="primary"):
        st.cache_data.clear()
        st.success("Cache cleared! Refreshing...")
        st.rerun()

    st.info(
        "Clearing the cache forces a fresh scan of all agents, runs, findings, "
        "and signal databases on the next page load."
    )
