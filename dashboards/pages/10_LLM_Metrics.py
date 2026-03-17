"""LLM Metrics — Model usage, cost, and performance."""

from __future__ import annotations

import streamlit as st
import pandas as pd

from dashboards.dashboard_data import load_all_runs, load_all_findings
from dashboards.components.theme import setup_page, apply_custom_css
from dashboards.components.filters import render_filters, get_active_filters
from dashboards.components.alerts import render_alert_bar
from dashboards.components.charts import cost_burn_chart

setup_page("LLM Metrics", "🤖")
apply_custom_css()

render_filters(show_agent_filter=True)

findings = load_all_findings()
render_alert_bar(findings)

st.header("LLM Metrics")
st.info(
    "Usage metrics extracted from agent run summaries. Configure tracing for deeper insights."
)

filters = get_active_filters()


def load_model_usage() -> list[dict]:
    """Extract model usage from run summaries."""
    usage = []
    for run in load_all_runs():
        if run.get("model_used"):
            usage.append(
                {
                    "agent": run.get("agent_name", run.get("agent", "")),
                    "model": run.get("model_used", ""),
                    "cost": run.get("model_cost_usd", 0),
                    "cost_usd": run.get("model_cost_usd", 0),
                    "duration": run.get("duration_seconds", 0),
                    "task": run.get("task_name", run.get("skill", "")),
                    "timestamp": run.get("started_at", run.get("completed_at", "")),
                }
            )
    return usage


usage = load_model_usage()

# Apply agent filter
if filters["agents"] and usage:
    usage = [u for u in usage if u.get("agent") in filters["agents"]]

if usage:
    col1, col2, col3 = st.columns(3)
    total_cost = sum(item.get("cost", 0) for item in usage)
    col1.metric("Total LLM Cost", f"${total_cost:.4f}")
    models = {item.get("model", "") for item in usage}
    col2.metric("Models Used", len(models))
    col3.metric("LLM-Assisted Runs", len(usage))

    st.divider()

    # Cost burn chart
    st.subheader("Cost Burn Over Time")
    burn_fig = cost_burn_chart(usage)
    st.plotly_chart(burn_fig, use_container_width=True)

    st.divider()
    st.subheader("Usage Analysis")
    usage_df = pd.DataFrame(usage)

    ucol1, ucol2 = st.columns(2)
    with ucol1:
        st.write("**Cost by Model**")
        cost_by_model = usage_df.groupby("model")["cost"].sum()
        st.bar_chart(cost_by_model)

    with ucol2:
        st.write("**Runs by Agent**")
        runs_by_agent = usage_df.groupby("agent").size()
        st.bar_chart(runs_by_agent)

    st.divider()
    st.subheader("Recent Usage Detail")
    st.dataframe(usage_df.head(50), use_container_width=True, hide_index=True)
else:
    st.write("No LLM usage data available yet.")

st.divider()
st.subheader("Model Configuration")
st.code(
    """llm:
  default_model: "claude-3-5-sonnet-latest"
  extraction_model: "gpt-4o-mini"
  fallback_model: "gemini-2.0-flash" """,
    language="yaml",
)
