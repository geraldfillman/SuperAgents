"""Simulations — Scenario builder, tick engine results, and MiroFish bundles."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from dashboards.dashboard_data import (
    PROJECT_ROOT,
    build_mirofish_embed_url,
    build_mirofish_publish_command,
    detect_mirofish_services,
    discover_simulation_bundles,
    discover_simulation_results,
    format_mirofish_publish_command,
    get_agent_sector,
)
from dashboards.components.theme import setup_page, apply_custom_css
from dashboards.components.filters import render_filters
from dashboards.components.alerts import render_alert_bar
from dashboards.dashboard_data import load_all_findings
from dashboards.components.cards import SimulationCard

setup_page("Simulations", "🎯")
apply_custom_css()

render_filters(show_agent_filter=False)

findings = load_all_findings()
render_alert_bar(findings)

st.header("Simulations")
st.caption(
    "Scenario engine results, MiroFish/Zep bundle management, and side-by-side comparison."
)

# ---------------------------------------------------------------------------
# Helpers (from old 09_Simulation_Engine)
# ---------------------------------------------------------------------------

def _extract_json_payload(output: str) -> dict | None:
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith("{"):
            candidate = "\n".join(lines[index:])
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    return None


def _run_publish(bundle_dir: Path) -> dict:
    command = build_mirofish_publish_command(bundle_dir)
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    payload = _extract_json_payload(completed.stdout)
    if completed.returncode != 0:
        error_text = completed.stderr.strip() or completed.stdout.strip() or "Unknown publish failure."
        raise RuntimeError(error_text)
    if not payload:
        raise RuntimeError("Publish command completed but did not return a JSON payload.")
    return payload


# ---------------------------------------------------------------------------
# Top metrics
# ---------------------------------------------------------------------------

results = discover_simulation_results()
bundles = discover_simulation_bundles()
services = detect_mirofish_services()
published_bundles = [b for b in bundles if b.get("published")]

mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("Scenario Results", len(results))
mc2.metric("MiroFish Bundles", len(bundles))
mc3.metric("Published to Zep", len(published_bundles))
mc4.metric(
    "MiroFish",
    "Online" if services["frontend_reachable"] else "Offline",
)

# ---------------------------------------------------------------------------
# Tabs: Scenario Builder | MiroFish Bundles
# ---------------------------------------------------------------------------

tab_scenarios, tab_bundles = st.tabs(["📊 Scenario Builder", "🎬 MiroFish Bundles"])

# ============================================================
# Tab 1: Scenario Builder (merged from 08_Scenario_Simulations)
# ============================================================

with tab_scenarios:
    if not results:
        st.info(
            "No simulation results found. Run a simulation:\n\n"
            "`python -m super_agents simulate scenarios/hormuz_zero_transit.yaml`"
        )
    else:
        st.sidebar.subheader("Comparison Mode")
        compare_enabled = st.sidebar.toggle("Enable Comparison", key="_sim_compare")

        results_by_name = {
            f"{r['scenario']} ({r['started_at'][:19]})": r for r in results
        }
        labels = list(results_by_name.keys())

        # --- Card grid ---
        st.subheader("All Simulation Results")
        card_cols = st.columns(3)
        for idx, r in enumerate(results):
            with card_cols[idx % 3]:
                SimulationCard(r)

        st.divider()
        st.subheader("Detailed View")

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

        def render_sim_overview(sim: dict, title_prefix: str = "") -> None:
            st.subheader(f"{title_prefix}Scenario: {sim['scenario']}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ticks", sim["tick_count"])
            c2.metric("Signals", sim["signal_count"])
            c3.metric("Alerts", len(sim.get("alerts", [])))
            c4.metric("Predictions", len(sim.get("predictions", [])))

        if not compare_enabled:
            render_sim_overview(sim1)
        else:
            st.divider()
            render_sim_overview(sim1, "Baseline: ")
            st.divider()
            render_sim_overview(sim2, "Comparison: ")

        # Variable evolution chart
        st.divider()
        st.subheader("Variable Evolution")

        def get_chart_data(sim: dict) -> tuple[list[int] | None, dict | None]:
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
            tick_len = len(ticks)
            numeric_vars = {k: v for k, v in numeric_vars.items() if len(v) == tick_len}
            return ticks, numeric_vars

        ticks1, vars1 = get_chart_data(sim1)
        if vars1:
            available = sorted(vars1.keys())
            selected_vars = st.multiselect("Variables to chart", available, default=available[:2])
            if selected_vars:
                chartable = [v for v in selected_vars if v in vars1]
                if not compare_enabled and chartable:
                    df = pd.DataFrame({v: vars1[v] for v in chartable}, index=ticks1)
                    st.line_chart(df)
                elif compare_enabled:
                    ticks2, vars2 = get_chart_data(sim2)
                    if vars2:
                        for v in chartable:
                            st.write(f"**Variable: {v}**")
                            baseline = vars1.get(v, [])
                            comparison = vars2.get(v, [])
                            max_len = max(len(baseline), len(comparison))
                            if len(baseline) < max_len:
                                baseline = baseline + [baseline[-1]] * (max_len - len(baseline))
                            if len(comparison) < max_len:
                                comparison = comparison + [comparison[-1]] * (max_len - len(comparison))
                            compare_df = pd.DataFrame({"Baseline": baseline, "Comparison": comparison})
                            st.line_chart(compare_df)

        st.divider()

        if not compare_enabled:
            tab_a, tab_p, tab_s = st.tabs(["Alerts", "Predictions", "Final State"])
            with tab_a:
                alerts = sim1.get("alerts", [])
                if alerts:
                    for a in alerts:
                        icon = "🚨" if a.get("severity") == "critical" else "⚠️"
                        st.write(
                            f"{icon} **Tick {a.get('tick', '?')}** — "
                            f"[{a.get('persona', '')}] {a.get('message', '')}"
                        )
                else:
                    st.info("No alerts generated.")
            with tab_p:
                predictions = sim1.get("predictions", [])
                if predictions:
                    for p in predictions:
                        st.write(
                            f"🔮 **Tick {p.get('tick', '?')}** — "
                            f"[{p.get('persona', '')}] {p.get('message', '')} "
                            f"(confidence: {p.get('confidence', 'N/A')})"
                        )
                else:
                    st.info("No predictions generated.")
            with tab_s:
                st.json(sim1.get("final_variables", {}))

# ============================================================
# Tab 2: MiroFish Bundles (merged from 09_Simulation_Engine)
# ============================================================

with tab_bundles:
    st.caption(
        "Portable MiroFish bundles from `data/processed/mirofish_simulations`. "
        "Published bundles can be opened in the local MiroFish app or embedded below."
    )

    if not bundles:
        st.info(
            "No simulation bundles found. "
            "Create a bundle under `data/processed/mirofish_simulations`."
        )
    else:
        bundles_by_id = {bundle["simulation_id"]: bundle for bundle in bundles}
        selected_id = st.selectbox(
            "Select Simulation Bundle",
            list(bundles_by_id),
            format_func=lambda sid: bundles_by_id[sid]["label"],
            key="_bundle_select",
        )
        selected = bundles_by_id[selected_id]
        embedded_process_url = build_mirofish_embed_url(selected.get("process_url"))

        summary_left, summary_right = st.columns(2)
        with summary_left:
            st.subheader(selected["label"])
            st.caption(selected.get("simulation_id", ""))
            st.write(selected.get("simulation_requirement", "No simulation requirement recorded."))
            st.caption(f"Bundle path: {selected['bundle_dir']}")
        with summary_right:
            metrics = st.columns(4)
            metrics[0].metric("Agents", selected.get("agent_count", 0))
            metrics[1].metric("Twitter", selected.get("action_counts", {}).get("twitter", 0))
            metrics[2].metric("Reddit", selected.get("action_counts", {}).get("reddit", 0))
            metrics[3].metric(
                "Graph Status", "Published" if selected.get("published") else "Bundle Only"
            )
            st.write(f"Graph ID: {selected.get('graph_id', 'Not published yet')}")
            st.write(
                f"Nodes: {selected.get('node_count', 0)} | Edges: {selected.get('edge_count', 0)}"
            )

        if selected.get("process_url") and services["frontend_reachable"]:
            st.divider()
            st.subheader("Embedded MiroFish Graph View")
            components.iframe(
                embedded_process_url or selected["process_url"], height=700, scrolling=True
            )

        st.divider()
        st.subheader("All Bundles")
        for bundle in bundles:
            status = "Published" if bundle.get("published") else "Bundle Only"
            title = (
                f"{bundle['label']} — {status} — "
                f"{bundle.get('action_counts', {}).get('twitter', 0) + bundle.get('action_counts', {}).get('reddit', 0)} actions"
            )
            with st.expander(title):
                st.write(f"Simulation ID: {bundle.get('simulation_id', '')}")
                st.write(f"Project ID: {bundle.get('project_id', 'N/A')}")
                st.write(f"Graph ID: {bundle.get('graph_id', 'N/A')}")
                st.write(f"Platforms: {', '.join(bundle.get('platforms', [])) or 'N/A'}")
                st.caption(str(bundle.get("bundle_dir", "")))
