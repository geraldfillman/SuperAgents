"""Scenario Simulations — View and compare simulation results from the engine."""

from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboards.dashboard_data import (
    discover_simulation_results,
    get_agent_sector,
)
from dashboards.components.theme import setup_page, apply_custom_css

setup_page("Scenario Simulations", "🎭")
apply_custom_css()

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

# ---------------------------------------------------------------------------
# Phase 3: Comparison Mode
# ---------------------------------------------------------------------------
st.sidebar.divider()
st.sidebar.subheader("Comparison Mode")
compare_enabled = st.sidebar.toggle("Enable Comparison")

# ---------------------------------------------------------------------------
# Select simulations
# ---------------------------------------------------------------------------

results_by_name = {
    f"{r['scenario']} ({r['started_at'][:19]})": r for r in results
}
labels = list(results_by_name.keys())

if compare_enabled:
    col1, col2 = st.columns(2)
    with col1:
        s1_label = st.selectbox("Baseline Simulation", labels, key="sim1")
        sim1 = results_by_name[s1_label]
    with col2:
        s2_label = st.selectbox("Comparison Simulation", labels, key="sim2")
        sim2 = results_by_name[s2_label]
else:
    selected_label = st.selectbox("Select Simulation", labels)
    sim1 = results_by_name[selected_label]
    sim2 = None

def render_sim_overview(sim, title_prefix=""):
    st.subheader(f"{title_prefix}Scenario: {sim['scenario']}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ticks", sim["tick_count"])
    col2.metric("Signals", sim["signal_count"])
    col3.metric("Alerts", len(sim.get("alerts", [])))
    col4.metric("Predictions", len(sim.get("predictions", [])))

if not compare_enabled:
    render_sim_overview(sim1)
else:
    st.divider()
    render_sim_overview(sim1, "Baseline: ")
    st.divider()
    render_sim_overview(sim2, "Comparison: ")

# ---------------------------------------------------------------------------
# Visualizations
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Variable Evolution")

def get_chart_data(sim):
    var_history = sim.get("variable_history", [])
    if not var_history or len(var_history) <= 1:
        return None, None

    numeric_vars: dict[str, list[float]] = {}
    ticks: list[int] = []
    for entry in var_history:
        ticks.append(entry.get("tick", 0))
        for var_name, var_value in entry.get("variables", {}).items():
            try:
                numeric_vars.setdefault(var_name, []).append(float(var_value))
            except (ValueError, TypeError):
                pass
    # Only keep vars whose length matches ticks (some vars may appear mid-run)
    tick_len = len(ticks)
    numeric_vars = {k: v for k, v in numeric_vars.items() if len(v) == tick_len}
    return ticks, numeric_vars

ticks1, vars1 = get_chart_data(sim1)

if vars1:
    available = sorted(vars1.keys())
    selected_vars = st.multiselect("Variables to chart", available, default=available[:2])

    if selected_vars:
        chartable = [v for v in selected_vars if v in vars1]
        if not compare_enabled:
            if chartable:
                df = pd.DataFrame({v: vars1[v] for v in chartable}, index=ticks1)
                st.line_chart(df)
        else:
            ticks2, vars2 = get_chart_data(sim2)
            if vars2:
                for v in chartable:
                    st.write(f"**Variable: {v}**")
                    baseline = vars1.get(v, [])
                    comparison = vars2.get(v, [])
                    max_len = max(len(baseline), len(comparison))
                    # Pad shorter series with last known value
                    if len(baseline) < max_len:
                        baseline = baseline + [baseline[-1]] * (max_len - len(baseline))
                    if len(comparison) < max_len:
                        comparison = comparison + [comparison[-1]] * (max_len - len(comparison))
                    compare_df = pd.DataFrame({"Baseline": baseline, "Comparison": comparison})
                    st.line_chart(compare_df)

st.divider()

# ---------------------------------------------------------------------------
# Alerts, predictions, and final state
# ---------------------------------------------------------------------------

if not compare_enabled:
    tab_alerts, tab_preds, tab_state = st.tabs(["Alerts", "Predictions", "Final State"])

    with tab_alerts:
        alerts = sim1.get("alerts", [])
        if alerts:
            for a in alerts:
                icon = "\U0001f6a8" if a.get("severity") == "critical" else "\u26a0\ufe0f"
                st.write(
                    f"{icon} **Tick {a.get('tick', '?')}** \u2014 "
                    f"[{a.get('persona', '')}] {a.get('message', '')}"
                )
        else:
            st.info("No alerts generated.")

    with tab_preds:
        predictions = sim1.get("predictions", [])
        if predictions:
            for p in predictions:
                st.write(
                    f"\U0001f52e **Tick {p.get('tick', '?')}** \u2014 "
                    f"[{p.get('persona', '')}] {p.get('message', '')} "
                    f"(confidence: {p.get('confidence', 'N/A')})"
                )
        else:
            st.info("No predictions generated.")

    with tab_state:
        st.json(sim1.get("final_variables", {}))
