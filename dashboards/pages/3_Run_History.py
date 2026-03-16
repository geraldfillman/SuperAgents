"""Run History — Past runs across all agents."""

from pathlib import Path

import streamlit as st

from dashboards.dashboard_data import discover_runnable_agents, load_all_runs

st.set_page_config(page_title="Run History", layout="wide")
st.header("Run History")

discovered_agents = discover_runnable_agents()
agent_names = [agent["name"] for agent in discovered_agents]
runs = load_all_runs()

if not runs:
    st.info("No run history yet. Execute agent workflows to generate run data.")
    if agent_names:
        st.caption(f"Runnable agents waiting for first run artifact: {', '.join(agent_names)}")
else:
    col1, col2 = st.columns(2)
    selected_agent = col1.selectbox("Filter by Agent", ["All"] + agent_names)
    statuses = sorted({run.get("status", "") for run in runs if run.get("status")})
    selected_status = col2.selectbox("Filter by Status", ["All"] + statuses)

    filtered = runs
    if selected_agent != "All":
        filtered = [run for run in filtered if run.get("agent_name") == selected_agent]
    if selected_status != "All":
        filtered = [run for run in filtered if run.get("status") == selected_status]

    agents_with_runs = {run.get("agent_name", "") for run in runs if run.get("agent_name")}
    missing_history = [name for name in agent_names if name not in agents_with_runs]
    if missing_history:
        st.caption(f"Agents with no run history yet: {', '.join(missing_history)}")

    st.write(f"Showing {len(filtered)} runs")

    if not filtered:
        st.info("No runs match the selected filters yet.")
    else:
        for run in filtered[:50]:
            status_icon = {"completed": "✅", "failed": "❌", "running": "🔄"}.get(
                run.get("status", ""),
                "⚪",
            )
            label = (
                f"{status_icon} {run.get('agent_name', 'unknown')} / "
                f"{run.get('task_name', 'unknown')} — "
                f"{run.get('duration_seconds', 0)}s"
            )
            with st.expander(label):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Agent", run.get("agent_name", ""))
                col2.metric("Workflow", run.get("workflow_name", ""))
                col3.metric("Duration", f"{run.get('duration_seconds', 0)}s")
                outputs = run.get("outputs", {})
                col4.metric("Records", outputs.get("records_written", 0))

                blockers = run.get("blockers", [])
                if blockers:
                    st.warning(f"Blockers: {', '.join(str(blocker) for blocker in blockers)}")

                md_path = run.get("_md_path")
                if md_path and Path(md_path).exists():
                    st.markdown(Path(md_path).read_text(encoding="utf-8"))
