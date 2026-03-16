"""Agent Detail — Deep dive into a specific agent."""

import streamlit as st

from dashboards.dashboard_data import (
    discover_runnable_agents,
    load_agent_findings,
    load_agent_latest_run,
    load_agent_status,
)

st.set_page_config(page_title="Agent Detail", layout="wide")
st.header("Agent Detail View")

agents = discover_runnable_agents()
if not agents:
    st.warning("No runnable agents were discovered.")
    st.stop()

agents_by_name = {agent["name"]: agent for agent in agents}
agent_names = list(agents_by_name)

selected = st.sidebar.selectbox(
    "Select Agent",
    agent_names,
    format_func=lambda name: agents_by_name[name]["label"],
)
agent = agents_by_name[selected]

col1, col2, col3 = st.columns(3)
col1.metric("Skills", agent["skill_count"])
col2.metric("Scripts", agent["script_count"])
col3.metric("Workflows", agent["workflow_count"])
st.caption(agent["description"])

status = load_agent_status(selected)
latest_run = load_agent_latest_run(selected)

left, right = st.columns(2)

with left:
    st.subheader("Current Task")
    if status:
        st.write(f"**Workflow**: {status.get('workflow_name', 'N/A')}")
        st.write(f"**Task**: {status.get('task_name', 'N/A')}")
        st.write(f"**Status**: {status.get('status', 'N/A')}")
        progress = status.get("progress", {})
        total = progress.get("total", 0)
        completed = progress.get("completed", 0)
        if total > 0:
            st.progress(completed / total, text=f"{completed}/{total}")
        st.write(f"**Focus**: {status.get('current_focus', 'N/A')}")
        st.write(f"**Latest**: {status.get('latest_message', 'N/A')}")
    else:
        st.info(f"No current-status artifact for {agent['label']} yet.")

with right:
    st.subheader("Latest Run")
    if latest_run:
        st.write(f"**Workflow**: {latest_run.get('workflow_name', 'N/A')}")
        st.write(f"**Task**: {latest_run.get('task_name', 'N/A')}")
        st.write(f"**Status**: {latest_run.get('status', 'N/A')}")
        st.write(f"**Duration**: {latest_run.get('duration_seconds', 0)}s")
        outputs = latest_run.get("outputs", {})
        st.write(f"**Records Written**: {outputs.get('records_written', 0)}")
        st.write(f"**Files Written**: {outputs.get('files_written', 0)}")
        next_actions = latest_run.get("next_actions", [])
        if next_actions:
            st.write(f"**Next Actions**: {', '.join(next_actions[:3])}")
    else:
        st.info(f"No latest-run artifact for {agent['label']} yet.")

st.subheader("Sources & Scope")
if status:
    st.write(f"**Active Source**: {status.get('active_source', 'N/A')}")
    scope = status.get("input_scope", [])
    if scope:
        st.write("**Assets in Scope**:")
        for item in scope:
            st.write(f"  - {item}")
    blocker = status.get("blocker")
    if blocker:
        st.error(f"**Blocker**: {blocker}")
else:
    st.caption("Source and scope data will appear once a current-status artifact is written.")

st.divider()

st.subheader("Latest Findings")
findings = load_agent_findings(selected)
if findings:
    for finding in findings[:20]:
        severity = finding.get("severity", "info")
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "info": "🔵"}.get(severity, "⚪")
        st.write(
            f"{icon} **[{finding.get('finding_type', 'unknown')}]** "
            f"{finding.get('asset', '')} — {finding.get('summary', '')}"
        )
        st.caption(
            f"Source: {finding.get('source_url', 'N/A')} | "
            f"Confidence: {finding.get('confidence', 'N/A')}"
        )
else:
    st.info(f"No findings artifact for {agent['label']} yet.")
