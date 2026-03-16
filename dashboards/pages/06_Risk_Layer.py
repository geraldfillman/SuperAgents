"""Global Risk Layer — Unified cross-sector signal dashboard.

Wired to real Crucix SignalStore when available; falls back gracefully.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from dashboards.components.risk_badge import get_risk_context, render_risk_badge
from dashboards.components.theme import setup_page, apply_custom_css, get_severity_icon
from dashboards.components.empty_state import render_empty_state
from dashboards.dashboard_data import (
    load_all_findings,
    load_crucix_signal_stats,
    load_crucix_status,
    discover_agent_names,
)

setup_page("Risk Layer", "\U0001f6e1\ufe0f")
apply_custom_css()

st.header("Global Risk Layer")
st.caption(
    "Cross-sector risk signals from Crucix (sanctions, conflict, weather, cyber). "
    "Entities tracked by agents are cross-referenced here."
)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

crucix = load_crucix_status()
signal_stats = load_crucix_signal_stats()
agent_names = discover_agent_names()
findings = load_all_findings(agent_names)

total_signals = signal_stats.get("total_signals", 0)
has_real_data = total_signals > 0

# ---------------------------------------------------------------------------
# Top metrics
# ---------------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)
col1.metric("Signal Source", "Live" if has_real_data else "Mock Fallback")
col2.metric("Stored Signals", total_signals)
col3.metric("Fleet Findings", len(findings))
col4.metric(
    "Action Required",
    sum(1 for f in findings if f.get("action_required")),
)

if not has_real_data:
    st.warning(
        "No Crucix signals stored yet. Signal panels show placeholder data. "
        "Run a sweep to populate: `python -m super_agents crucix sweep --store`"
    )

# ---------------------------------------------------------------------------
# Entity search
# ---------------------------------------------------------------------------

st.divider()
search_query = st.text_input(
    "Entity Search",
    placeholder="Type a company, vessel, or country name...",
)

if search_query:
    risk = get_risk_context(search_query, "Global")
    st.subheader(f"Risk Context: {search_query}")

    res1, res2, res3, res4 = st.columns(4)
    res1.metric("Sanctions Hit", "YES" if risk["sanctions_hit"] else "NO")
    res2.metric("Conflict Proximity", "HIGH" if risk["conflict_nearby"] else "LOW")
    res3.metric("Cyber Exposure", "YES" if risk["cyber_alert"] else "LOW")
    res4.metric("Weather Impact", "YES" if risk["weather_hazard"] else "NONE")
    st.info(f"**Detail**: {risk['description']}")
    render_risk_badge(search_query, "Global")

# ---------------------------------------------------------------------------
# Signal panels — real data when available, findings-derived otherwise
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Active Signal Monitoring")

# Derive category counts from real findings
_categories: dict[str, list[dict]] = {
    "sanctions": [],
    "conflict": [],
    "weather": [],
    "cyber": [],
}

for f in findings:
    ftype = (f.get("finding_type") or "").lower()
    summary = (f.get("summary") or "").lower()
    if "sanction" in ftype or "sanction" in summary:
        _categories["sanctions"].append(f)
    elif "conflict" in ftype or "military" in summary or "geopolitical" in summary:
        _categories["conflict"].append(f)
    elif "weather" in ftype or "fire" in summary or "storm" in summary:
        _categories["weather"].append(f)
    elif "cyber" in ftype or "cve" in summary or "vulnerability" in summary:
        _categories["cyber"].append(f)

p1, p2, p3, p4 = st.columns(4)

with p1:
    st.markdown("### \U0001f6ab Sanctions")
    st.caption("OFAC + OpenSanctions")
    items = _categories["sanctions"]
    if items:
        for item in items[:5]:
            st.write(f"- {get_severity_icon(item.get('severity', 'info'))} {item.get('summary', '')[:80]}")
    else:
        st.caption("No sanctions signals detected.")

with p2:
    st.markdown("### \u2694\ufe0f Conflict")
    st.caption("GDELT + ACLED")
    items = _categories["conflict"]
    if items:
        for item in items[:5]:
            st.write(f"- {get_severity_icon(item.get('severity', 'info'))} {item.get('summary', '')[:80]}")
    else:
        st.caption("No conflict signals detected.")

with p3:
    st.markdown("### \U0001f326\ufe0f Weather")
    st.caption("NWS + NASA FIRMS")
    items = _categories["weather"]
    if items:
        for item in items[:5]:
            st.write(f"- {get_severity_icon(item.get('severity', 'info'))} {item.get('summary', '')[:80]}")
    else:
        st.caption("No weather signals detected.")

with p4:
    st.markdown("### \U0001f6e1\ufe0f Cyber")
    st.caption("CISA KEV + IODA")
    items = _categories["cyber"]
    if items:
        for item in items[:5]:
            st.write(f"- {get_severity_icon(item.get('severity', 'info'))} {item.get('summary', '')[:80]}")
    else:
        st.caption("No cyber signals detected.")

# ---------------------------------------------------------------------------
# Signal distribution chart
# ---------------------------------------------------------------------------

st.divider()
cat_counts = {k: len(v) for k, v in _categories.items()}
if any(cat_counts.values()):
    st.subheader("Signal Category Distribution")
    chart_df = pd.Series(cat_counts, name="Signals")
    st.bar_chart(chart_df)

# ---------------------------------------------------------------------------
# Watchlist — real findings with action_required
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Watchlist Entities")

action_findings = [f for f in findings if f.get("action_required")]

if action_findings:
    for f in action_findings[:15]:
        severity = f.get("severity", "info")
        agent = f.get("_agent", "unknown")
        asset = f.get("asset", f.get("summary", "")[:60])
        c1, c2, c3 = st.columns([3, 1, 2])
        with c1:
            st.write(f"{get_severity_icon(severity)} **{asset}**")
        with c2:
            st.caption(agent)
        with c3:
            st.caption(f.get("finding_time", ""))
else:
    render_empty_state(
        "No action-required findings across the fleet.",
        "python -m super_agents search --verbose",
    )
