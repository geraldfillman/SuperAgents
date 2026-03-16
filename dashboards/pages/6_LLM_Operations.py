"""LLM Operations — Model usage, cost, and performance."""

import streamlit as st

from dashboards.dashboard_data import load_all_runs

st.set_page_config(page_title="LLM Operations", layout="wide")
st.header("LLM Operations")

st.info(
    "This page will display LLM usage metrics once Langfuse tracing is configured. "
    "Set LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY environment variables to enable."
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

    st.subheader("Usage by Model")
    model_stats: dict[str, dict] = {}
    for item in usage:
        model = item.get("model", "unknown")
        if model not in model_stats:
            model_stats[model] = {"runs": 0, "cost": 0.0, "total_duration": 0.0}
        model_stats[model]["runs"] += 1
        model_stats[model]["cost"] += item.get("cost", 0)
        model_stats[model]["total_duration"] += item.get("duration", 0)

    for model, stats in sorted(model_stats.items()):
        st.write(
            f"**{model}**: {stats['runs']} runs | "
            f"${stats['cost']:.4f} total cost | "
            f"{stats['total_duration']:.1f}s total duration"
        )
else:
    st.write("No LLM usage data available yet.")

st.divider()
st.subheader("Model Configuration")
st.markdown(
    """
The LLM layer uses **LiteLLM** for model-agnostic operation. Configure per agent in `config.yaml`:

```yaml
llm:
  default_model: "claude-sonnet-4-20250514"
  extraction_model: "gpt-4o-mini"
  scoring_model: "claude-sonnet-4-20250514"
  fallback_model: "gemini-2.0-flash"
```

Supported providers: Anthropic, OpenAI, Google, Azure, Bedrock, Ollama, and 100+ more via LiteLLM.
"""
)
