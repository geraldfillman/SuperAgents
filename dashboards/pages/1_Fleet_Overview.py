"""Fleet Overview — All runnable agents organized by sector."""

import streamlit as st

from dashboards.dashboard_data import (
    AGENT_SECTOR_MAP,
    discover_runnable_agents,
    get_agent_sector,
    group_agents_by_sector,
    load_agent_latest_run,
    load_agent_status,
    load_crucix_status,
)

st.set_page_config(page_title="Fleet Overview", layout="wide")
st.header("Agent Fleet Overview")

agents = discover_runnable_agents()

if not agents:
    st.warning("No runnable agents were discovered. Check `.agent_*` skill scripts.")
    st.stop()

agents_with_status = sum(1 for agent in agents if load_agent_status(agent["name"]))
agents_with_latest_run = sum(1 for agent in agents if load_agent_latest_run(agent["name"]))
crucix = load_crucix_status()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Runnable Agents", len(agents))
col2.metric("Agents With Status", agents_with_status)
col3.metric("Agents With Runs", agents_with_latest_run)
col4.metric("Crucix Data Hub", "Connected" if crucix["installed"] else "Not Installed")

st.caption(
    "Agents discovered from `.agent_*` folders, organized by sector. "
    "Each agent has skills with runnable Python scripts."
)

# ---------------------------------------------------------------------------
# Sector-organized agent grid
# ---------------------------------------------------------------------------

grouped = group_agents_by_sector(agents)

for group_name, group_agents in grouped.items():
    st.divider()
    st.subheader(group_name)

    cards_per_row = 3
    for start in range(0, len(group_agents), cards_per_row):
        row = group_agents[start : start + cards_per_row]
        cols = st.columns(len(row))
        for col, agent in zip(cols, row):
            with col:
                sector = get_agent_sector(agent["name"])
                status = load_agent_status(agent["name"])
                latest_run = load_agent_latest_run(agent["name"])

                # Agent header with sector icon
                st.markdown(
                    f"### {sector['icon']} {agent['label']}"
                )
                st.caption(sector.get("description", agent["description"]))
                st.caption(
                    f"Skills: {agent['skill_count']} | Scripts: {agent['script_count']} | "
                    f"Workflows: {agent['workflow_count']}"
                )

                if status:
                    state = status.get("status", "unknown")
                    color = {
                        "running": "🟢",
                        "completed": "🔵",
                        "failed": "🔴",
                        "idle": "⚪",
                    }.get(state, "⚪")
                    st.metric("Status", f"{color} {state}")
                    progress = status.get("progress", {})
                    total = progress.get("total", 0)
                    completed = progress.get("completed", 0)
                    if total > 0:
                        st.progress(completed / total, text=f"{completed}/{total}")
                    st.caption(f"Task: {status.get('task_name', 'N/A')}")
                else:
                    st.info("No status artifact yet.")

                if latest_run:
                    outputs = latest_run.get("outputs", {})
                    st.caption(
                        f"Latest: {latest_run.get('task_name', 'N/A')} "
                        f"({latest_run.get('status', 'unknown')}) | "
                        f"Records: {outputs.get('records_written', 0)}"
                    )
                else:
                    st.caption("No run history yet.")

# ---------------------------------------------------------------------------
# Sector coverage summary
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Sector Coverage")

agent_names = {a["name"] for a in agents}
sector_cols = st.columns(5)
for idx, (sector_name, sector_info) in enumerate(AGENT_SECTOR_MAP.items()):
    col = sector_cols[idx % 5]
    with col:
        has_agent = sector_name in agent_names
        status_icon = "✅" if has_agent else "⬜"
        st.markdown(f"{sector_info['icon']} **{sector_name}** {status_icon}")

# ---------------------------------------------------------------------------
# Latest run summaries
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Latest Run Summaries")
latest_runs: list[tuple[dict, dict]] = []
for agent in agents:
    latest_run = load_agent_latest_run(agent["name"])
    if latest_run:
        latest_runs.append((agent, latest_run))

if not latest_runs:
    st.info("No latest-run artifacts yet. Execute an agent workflow to populate this view.")
else:
    latest_runs.sort(
        key=lambda item: (
            item[1].get("completed_at", ""),
            item[1].get("started_at", ""),
            item[1].get("run_id", ""),
        ),
        reverse=True,
    )
    for agent, latest_run in latest_runs:
        sector = get_agent_sector(agent["name"])
        title = (
            f"{sector['icon']} {agent['label']} - {latest_run.get('task_name', 'N/A')} "
            f"({latest_run.get('status', 'unknown')})"
        )
        with st.expander(title):
            col1, col2, col3 = st.columns(3)
            outputs = latest_run.get("outputs", {})
            col1.metric("Duration", f"{latest_run.get('duration_seconds', 0)}s")
            col2.metric("Records", outputs.get("records_written", 0))
            col3.metric("Findings", len(latest_run.get("findings", [])))

            for finding in latest_run.get("findings", [])[:5]:
                st.write(
                    f"- [{finding.get('severity', 'info')}] "
                    f"{finding.get('summary', str(finding))}"
                )
