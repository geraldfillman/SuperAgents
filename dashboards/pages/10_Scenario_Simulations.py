"""Scenario Simulations — View and compare simulation results from the engine."""

from __future__ import annotations

import streamlit as st

from dashboards.dashboard_data import (
    discover_simulation_results,
    get_agent_sector,
)

st.set_page_config(page_title="Scenario Simulations", layout="wide")
st.header("Scenario Simulations")
st.caption(
    "Results from the tick-based simulation engine. "
    "Each simulation runs personas through a YAML-defined scenario with Crucix signals."
)

# ---------------------------------------------------------------------------
# Discover results
# ---------------------------------------------------------------------------

results = discover_simulation_results()

if not results:
    st.info(
        "No simulation results found. Run a simulation with:\n\n"
        "`python -m super_agents simulate scenarios/hormuz_zero_transit.yaml`"
    )
    st.stop()

st.metric("Simulation Runs", len(results))

# ---------------------------------------------------------------------------
# Select a simulation
# ---------------------------------------------------------------------------

results_by_name = {
    f"{r['scenario']} ({r['started_at'][:19]})": r for r in results
}
selected_label = st.selectbox("Select Simulation", list(results_by_name.keys()))
sim = results_by_name[selected_label]

# ---------------------------------------------------------------------------
# Overview metrics
# ---------------------------------------------------------------------------

st.divider()
st.subheader(f"Scenario: {sim['scenario']}")
st.caption(sim.get("description", ""))

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Ticks", sim["tick_count"])
col2.metric("Signals", sim["signal_count"])
col3.metric("Alerts", len(sim.get("alerts", [])))
col4.metric("Predictions", len(sim.get("predictions", [])))
col5.metric("Hypotheses", len(sim.get("hypotheses", [])))

# Hypotheses
if sim.get("hypotheses"):
    st.markdown("**Hypotheses:**")
    for h in sim["hypotheses"]:
        st.markdown(f"- {h}")

# ---------------------------------------------------------------------------
# Variable evolution chart
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Variable Evolution")

var_history = sim.get("variable_history", [])
final_vars = sim.get("final_variables", {})

if var_history and len(var_history) > 1:
    # Build chart data - extract numeric variables
    numeric_vars: dict[str, list[float]] = {}
    ticks: list[int] = []

    for entry in var_history:
        ticks.append(entry.get("tick", 0))
        for var_name, var_value in entry.get("variables", {}).items():
            try:
                numeric_vars.setdefault(var_name, []).append(float(var_value))
            except (ValueError, TypeError):
                pass

    if numeric_vars:
        # Let user pick which variables to chart
        available = sorted(numeric_vars.keys())
        default_vars = [v for v in available if any(
            k in v for k in ("price", "vix", "rate", "pct", "yield")
        )][:4]
        if not default_vars:
            default_vars = available[:4]

        selected_vars = st.multiselect(
            "Variables to chart",
            available,
            default=default_vars,
        )

        if selected_vars:
            import pandas as pd

            chart_data = pd.DataFrame(
                {var: numeric_vars[var] for var in selected_vars if var in numeric_vars},
                index=ticks,
            )
            chart_data.index.name = "Tick"
            st.line_chart(chart_data)

# Final state table
st.markdown("**Final Variable State:**")
if final_vars:
    var_cols = st.columns(min(4, len(final_vars)))
    for idx, (var_name, var_value) in enumerate(sorted(final_vars.items())):
        col = var_cols[idx % len(var_cols)]
        with col:
            st.metric(var_name, str(var_value))

# ---------------------------------------------------------------------------
# Alerts timeline
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Alerts")

alerts = sim.get("alerts", [])
if alerts:
    for alert in alerts:
        persona = alert.get("persona", "")
        sector = get_agent_sector(persona.replace("_analyst", "").replace("_officer", "").replace("_trader", ""))
        severity_icon = "🔴" if "CRITICAL" in alert.get("alert", "") else "🟠"

        st.markdown(
            f"{severity_icon} **Tick {alert.get('tick', '?')}** "
            f"[{sector.get('icon', '📦')} {persona}] "
            f"(conf: {alert.get('confidence', 0):.0%})"
        )
        st.markdown(f"  {alert.get('alert', '')}")
else:
    st.info("No alerts generated in this simulation.")

# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Predictions")

predictions = sim.get("predictions", [])
if predictions:
    for pred in predictions:
        persona = pred.get("persona", "")
        text = pred.get("text", str(pred))
        st.markdown(
            f"**Tick {pred.get('tick', '?')}** [{persona}] "
            f"(conf: {pred.get('confidence', 0):.0%}): {text}"
        )
else:
    st.info("No predictions generated in this simulation.")

# ---------------------------------------------------------------------------
# Tick-by-tick detail
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Tick-by-Tick Detail")

ticks_data = sim.get("ticks", [])
if ticks_data:
    for tick in ticks_data:
        tick_num = tick.get("tick", 0)
        tick_time = tick.get("time", "")[:19]
        assessments = tick.get("assessments", [])
        alert_count = sum(len(a.get("alerts", [])) for a in assessments)
        pred_count = sum(len(a.get("predictions", [])) for a in assessments)

        label = (
            f"Tick {tick_num} ({tick_time}) - "
            f"{len(assessments)} personas, {alert_count} alerts, {pred_count} predictions"
        )

        with st.expander(label):
            for assessment in assessments:
                persona = assessment.get("persona", "unknown")
                confidence = assessment.get("confidence", 0)
                st.markdown(f"**{persona}** (confidence: {confidence:.0%})")

                observations = assessment.get("observations", [])
                if observations:
                    for obs in observations[:8]:
                        st.markdown(f"- {obs}")

                reasoning = assessment.get("reasoning", "")
                if reasoning:
                    st.caption(f"Reasoning: {reasoning}")

                st.markdown("---")

# ---------------------------------------------------------------------------
# CLI reference
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Run Simulations")
st.code(
    """# Run with console summary
python -m super_agents simulate scenarios/hormuz_zero_transit.yaml --summary

# Run with full JSON + Markdown output
python -m super_agents simulate scenarios/hormuz_zero_transit.yaml

# Inject Crucix signals into simulation
python -m super_agents simulate scenarios/hormuz_zero_transit.yaml --from-store

# Custom output directory
python -m super_agents simulate scenarios/hormuz_zero_transit.yaml -o output/""",
    language="bash",
)
