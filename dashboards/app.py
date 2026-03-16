"""Super Agents — Interactive Monitoring Dashboard.

Launch: streamlit run dashboards/app.py
"""

from __future__ import annotations

import streamlit as st

from dashboards.dashboard_data import (
    detect_mirofish_services,
    discover_runnable_agents,
    discover_simulation_bundles,
    discover_simulation_results,
    group_agents_by_sector,
    load_all_findings,
    load_all_runs,
    load_crucix_status,
)
from dashboards.components.theme import setup_page, apply_custom_css

setup_page("Super Agents Dashboard", "\U0001f52c")
apply_custom_css()

st.title("Super Agents \u2014 Multi-Sector Intelligence Platform")
st.markdown("""
| Group | Pages | Purpose |
|-------|-------|---------|
| **Monitoring** | 01\u201303 | Fleet status, agent details, execution history |
| **Intelligence** | 04\u201306 | Findings board, Crucix signal routing, global risk layer |
| **Planning** | 07\u201309 | Calendars, scenario simulations, MiroFish bundles |
| **Operations** | 10\u201312 | Cybersecurity, LLM metrics, system settings |
""")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

agents = discover_runnable_agents()
runs = load_all_runs()
findings = load_all_findings()
simulation_bundles = discover_simulation_bundles()
mirofish_services = detect_mirofish_services()
crucix = load_crucix_status()
scenario_results = discover_simulation_results()

# ---------------------------------------------------------------------------
# Top metrics
# ---------------------------------------------------------------------------

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Agents", len(agents))
col2.metric("Tracked Runs", len(runs))
col3.metric("Crucix", "Active" if crucix["installed"] else "Setup Needed")
col4.metric("Findings", len(findings))
col5.metric("Simulations", len(scenario_results))
col6.metric("MiroFish Bundles", len(simulation_bundles))

# ---------------------------------------------------------------------------
# Sector overview
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Sector Coverage")

grouped = group_agents_by_sector(agents)
for group_name, group_agents in grouped.items():
    agent_names = ", ".join(a["label"] for a in group_agents)
    st.markdown(f"**{group_name}:** {agent_names}")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.header("Navigation")
st.sidebar.info("Select a page from the sidebar above.")

st.sidebar.divider()
st.sidebar.subheader("Quick Status")

if crucix["installed"]:
    st.sidebar.success("Crucix: Installed")
else:
    st.sidebar.warning("Crucix: Not installed")

action_count = sum(1 for f in findings if f.get("action_required"))
st.sidebar.caption(
    f"Agents: {len(agents)} | Runs: {len(runs)} | Action items: {action_count}"
)
