"""Settings — System health, configurations, alert rules, and cache management."""

from __future__ import annotations

import sys

import streamlit as st

from dashboards.dashboard_data import (
    PROJECT_ROOT,
    CRUCIX_SIGNALS_DB,
    detect_mirofish_services,
    discover_runnable_agents,
    load_all_findings,
    load_crucix_signal_stats,
    load_crucix_status,
)
from dashboards.components.theme import DASHBOARD_VERSION, NAV_GROUPS, setup_page, apply_custom_css
from dashboards.components.alerts import render_alert_bar

setup_page("Settings", "⚙️")
apply_custom_css()

findings = load_all_findings()
render_alert_bar(findings)

st.header("System Settings")
st.caption(f"Dashboard v{DASHBOARD_VERSION}")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Health & Config", "Alert Rules", "CLI Cheatsheet", "Cache Management"]
)

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
        st.write(f"- Crucix: {'✅ Installed' if crucix['installed'] else '❌ Missing'}")
        st.write(f"- Signal DB: {'✅ Active' if crucix['signals_db_exists'] else '❌ Missing'}")
        st.write(f"- Signals stored: {signal_stats.get('total_signals', 0)}")
        st.write(f"- Agents discovered: {len(agents)}")

    with h2:
        st.markdown("**MiroFish Services**")
        st.write(f"- Frontend: {'✅ Up' if mirofish['frontend_reachable'] else '❌ Down'}")
        st.write(f"- Backend: {'✅ Up' if mirofish['backend_reachable'] else '❌ Down'}")
        st.write(f"- Runtime home: {'✅' if mirofish['runtime_home_exists'] else '❌'}")

    with h3:
        st.markdown("**Environment**")
        st.write(f"- Python: {sys.version.split()[0]}")
        st.write(f"- Project root: `{PROJECT_ROOT}`")
        st.write(f"- Signals DB: `{CRUCIX_SIGNALS_DB}`")

    st.divider()
    st.subheader("Navigation Groups")
    for group, pages in NAV_GROUPS.items():
        st.markdown(f"**{group}:** {', '.join(pages)}")

    st.divider()
    st.subheader("Agent Configuration Status")
    agent_rows = [
        {
            "Agent": a["label"],
            "Config": "✅" if a["config_exists"] else "❌",
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
# Tab 2 — Alert Rules
# ---------------------------------------------------------------------------

with tab2:
    st.subheader("Alert Rules")
    st.caption(
        "Configure which findings trigger the alert bar. "
        "Phase 2 will add email/Slack notifications."
    )

    _ALERT_KEY = "_alert_rule_min_severity"
    _ALERT_SECTORS_KEY = "_alert_rule_sectors"

    if _ALERT_KEY not in st.session_state:
        st.session_state[_ALERT_KEY] = "high"
    if _ALERT_SECTORS_KEY not in st.session_state:
        st.session_state[_ALERT_SECTORS_KEY] = []

    st.session_state[_ALERT_KEY] = st.selectbox(
        "Minimum severity to trigger alert bar",
        options=["critical", "high", "medium", "low"],
        index=["critical", "high", "medium", "low"].index(
            st.session_state[_ALERT_KEY]
        ),
        key="_settings_alert_severity",
    )

    from dashboards.dashboard_data import AGENT_SECTOR_MAP
    sector_opts = list(AGENT_SECTOR_MAP.keys())
    st.session_state[_ALERT_SECTORS_KEY] = st.multiselect(
        "Restrict alerts to sectors (empty = all sectors)",
        options=sector_opts,
        default=st.session_state[_ALERT_SECTORS_KEY],
        format_func=lambda s: f"{AGENT_SECTOR_MAP[s]['icon']} {s.replace('_', ' ').title()}",
        key="_settings_alert_sectors",
    )

    st.divider()
    st.subheader("Alert History")
    from dashboards.components.alerts import render_alert_history
    render_alert_history(findings)

# ---------------------------------------------------------------------------
# Tab 3 — CLI Cheatsheet
# ---------------------------------------------------------------------------

with tab3:
    st.subheader("CLI Commands")

    st.markdown("### 🏃 Running Agents")
    st.code(
        "python -m super_agents list\n"
        "python -m super_agents list --agent biotech\n"
        "python -m super_agents run --agent biotech --verbose\n"
        "python -m super_agents search --verbose",
        language="bash",
    )

    st.markdown("### 📡 Crucix Operations")
    st.code(
        "python -m super_agents crucix status\n"
        "python -m super_agents crucix setup\n"
        "python -m super_agents crucix sweep --store\n"
        "python -m super_agents crucix signals --topic maritime",
        language="bash",
    )

    st.markdown("### 🎭 Simulations")
    st.code(
        "python -m super_agents simulate scenarios/hormuz_zero_transit.yaml\n"
        "python -m super_agents simulate scenarios/hormuz_zero_transit.yaml --json-only",
        language="bash",
    )

    st.markdown("### 📊 Dashboard")
    st.code(
        "streamlit run dashboards/app.py",
        language="bash",
    )

# ---------------------------------------------------------------------------
# Tab 4 — Cache Management
# ---------------------------------------------------------------------------

with tab4:
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
