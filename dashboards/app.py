"""Super Agents — Interactive Monitoring Dashboard.

Launch: streamlit run dashboards/app.py
"""

import streamlit as st

from dashboards.dashboard_data import (
    detect_mirofish_services,
    discover_runnable_agents,
    discover_simulation_bundles,
    discover_simulation_results,
    group_agents_by_sector,
    load_all_runs,
    load_crucix_status,
)

st.set_page_config(
    page_title="Super Agents Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Super Agents — Multi-Sector Agent Monitor")
st.markdown("""
Welcome to the Super Agents monitoring dashboard. Use the sidebar to navigate:

- **Fleet Overview** — All agents organized by sector
- **Agent Detail** — Deep dive into a specific agent
- **Run History** — Past runs across all agents
- **Findings Board** — Rolling discoveries across sectors
- **Calendars** — Catalyst/release/program calendars
- **LLM Operations** — Model usage, cost, and performance
- **Simulation Engine** — Zep-backed MiroFish bundles
- **Cybersecurity** — Threat intelligence and patches
- **Crucix Data Hub** — Live intelligence from 27 data sources
- **Scenario Simulations** — What-if analysis with tick-based engine
""")

agents = discover_runnable_agents()
runs = load_all_runs()
simulation_bundles = discover_simulation_bundles()
published_simulations = [bundle for bundle in simulation_bundles if bundle.get("published")]
mirofish_services = detect_mirofish_services()
crucix = load_crucix_status()
scenario_results = discover_simulation_results()

# Top metrics
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Agents", len(agents))
col2.metric("Tracked Runs", len(runs))
col3.metric("Crucix", "Active" if crucix["installed"] else "Setup Needed")
col4.metric("Simulations", len(scenario_results))
col5.metric("MiroFish Bundles", len(simulation_bundles))
col6.metric("MiroFish Frontend", "Up" if mirofish_services["frontend_reachable"] else "Down")

# Sector overview
st.divider()
st.subheader("Sector Coverage")

grouped = group_agents_by_sector(agents)
for group_name, group_agents in grouped.items():
    agent_names = ", ".join(a["label"] for a in group_agents)
    st.markdown(f"**{group_name}:** {agent_names}")

# Latest activity
if published_simulations:
    latest_simulation = published_simulations[0]
    st.caption(
        "Latest published simulation: "
        f"{latest_simulation['label']} — "
        f"{latest_simulation.get('process_url', latest_simulation.get('graph_id', ''))}"
    )

if scenario_results:
    latest = scenario_results[0]
    st.caption(
        f"Latest scenario simulation: {latest['scenario']} — "
        f"{latest['tick_count']} ticks, {len(latest.get('alerts', []))} alerts"
    )

# Sidebar
st.sidebar.header("Navigation")
st.sidebar.info("Select a page from the sidebar above.")

st.sidebar.divider()
st.sidebar.subheader("Quick Status")

if crucix["installed"]:
    st.sidebar.success("Crucix: Installed")
else:
    st.sidebar.warning("Crucix: Not installed")

st.sidebar.caption(f"Agents: {len(agents)} | Runs: {len(runs)}")

st.sidebar.divider()
st.sidebar.caption("Super Agents v0.2.0 — Multi-Sector Agent Framework")
