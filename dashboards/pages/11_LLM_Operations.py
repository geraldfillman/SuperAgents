"""LLM Operations — Model usage, cost, and performance."""

import streamlit as st
import pandas as pd
from dashboards.dashboard_data import load_all_runs
from dashboards.components.theme import setup_page, apply_custom_css

setup_page("LLM Operations", "🤖")
apply_custom_css()

st.header("LLM Operations")

st.info(
    "Usage metrics extracted from agent run summaries. Configure tracing for deeper insights."
)

def load_model_usage() -> list[dict]:
    """Extract model usage from run summaries."""
    usage = []
    for run in load_all_runs():
        if run.get("model_used"):
            usage.append(
                {
                    "agent": run.get("agent_name", ""),
                    "model": run.get("model_used", ""),
                    "cost": run.get("model_cost_usd", 0),
                    "duration": run.get("duration_seconds", 0),
                    "task": run.get("task_name", ""),
                }
            )
    return usage

usage = load_model_usage()

if usage:
    col1, col2, col3 = st.columns(3)
    total_cost = sum(item.get("cost", 0) for item in usage)
    col1.metric("Total LLM Cost", f"${total_cost:.4f}")
    models = {item.get("model", "") for item in usage}
    col2.metric("Models Used", len(models))
    col3.metric("LLM-Assisted Runs", len(usage))

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
st.code("""llm:
  default_model: "claude-3-5-sonnet-latest"
  extraction_model: "gpt-4o-mini"
  fallback_model: "gemini-2.0-flash" """, language="yaml")
