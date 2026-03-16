"""Simulation Engine — MiroFish/Zep bundle visibility inside the Super Agents dashboard."""

from __future__ import annotations
import json
import subprocess
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from dashboards.dashboard_data import (
    PROJECT_ROOT,
    build_mirofish_embed_url,
    build_mirofish_publish_command,
    detect_mirofish_services,
    discover_simulation_bundles,
    format_mirofish_publish_command,
)
from dashboards.components.theme import setup_page, apply_custom_css

setup_page("Simulation Engine", "⚙️")
apply_custom_css()

st.header("Simulation Engine")

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

services = detect_mirofish_services()
bundles = discover_simulation_bundles()
published_bundles = [bundle for bundle in bundles if bundle.get("published")]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Simulation Bundles", len(bundles))
col2.metric("Published to Zep", len(published_bundles))
col3.metric("MiroFish Frontend", "Up" if services["frontend_reachable"] else "Down")
col4.metric("MiroFish Backend", "Up" if services["backend_reachable"] else "Down")

st.caption(
    "Portable MiroFish bundles discovered from "
    "`data/processed/mirofish_simulations`. Published bundles can be opened directly in the "
    "local MiroFish app or embedded below."
)

if not bundles:
    st.info("No simulation bundles found yet. Create a bundle under `data/processed/mirofish_simulations`.")
    st.stop()

bundles_by_id = {bundle["simulation_id"]: bundle for bundle in bundles}
selected_id = st.selectbox(
    "Select Simulation Bundle",
    list(bundles_by_id),
    format_func=lambda simulation_id: bundles_by_id[simulation_id]["label"],
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
    metrics[1].metric("Twitter Actions", selected.get("action_counts", {}).get("twitter", 0))
    metrics[2].metric("Reddit Actions", selected.get("action_counts", {}).get("reddit", 0))
    metrics[3].metric("Graph Status", "Published" if selected.get("published") else "Bundle Only")
    st.write(f"Graph ID: {selected.get('graph_id', 'Not published yet')}")
    st.write(f"Nodes: {selected.get('node_count', 0)} | Edges: {selected.get('edge_count', 0)}")

# Embed View
if selected.get("process_url") and services["frontend_reachable"]:
    st.divider()
    st.subheader("Embedded MiroFish Graph View")
    components.iframe(embedded_process_url or selected["process_url"], height=700, scrolling=True)

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
        st.caption(bundle.get("bundle_dir", ""))
