"""Run History — Past runs across all agents."""

from pathlib import Path
import streamlit as st
import pandas as pd

from dashboards.dashboard_data import discover_runnable_agents, load_all_runs
from dashboards.components.theme import setup_page, apply_custom_css, get_status_icon
from dashboards.components.empty_state import render_empty_state

setup_page("Run History", "📜")
apply_custom_css()

st.header("Run History")

discovered_agents = discover_runnable_agents()
agent_names = [agent["name"] for agent in discovered_agents]
runs = load_all_runs()

if not runs:
    render_empty_state(
        "No run history yet. Execute agent workflows to generate run data.",
        "python -m super_agents run --agent biotech --verbose"
    )
    if agent_names:
        st.caption(f"Runnable agents waiting for first run artifact: {', '.join(agent_names)}")
else:
    # ---------------------------------------------------------------------------
    # Phase 3: Visualizations (Success/Fail bars & Duration trend)
    # ---------------------------------------------------------------------------
    vcol1, vcol2 = st.columns(2)
    
    with vcol1:
        st.subheader("Execution Status")
        status_counts = pd.Series([r.get("status", "unknown") for r in runs]).value_counts()
        st.bar_chart(status_counts)
        
    with vcol2:
        st.subheader("System Performance")
        run_durations = [r.get("duration_seconds", 0) for r in reversed(runs[:20])]
        st.line_chart(run_durations)
        st.caption("Duration (seconds) for last 20 global runs")

    st.divider()

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
            status_icon = get_status_icon(run.get("status", ""))
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
