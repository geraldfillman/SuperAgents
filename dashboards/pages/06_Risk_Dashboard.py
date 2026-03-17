"""Risk Dashboard — Unified cross-sector signal dashboard with radar chart."""

from __future__ import annotations

import streamlit as st
import pandas as pd

from dashboards.components.risk_badge import get_risk_context, render_risk_badge
from dashboards.components.theme import setup_page, apply_custom_css, get_severity_icon
from dashboards.components.empty_state import render_empty_state
from dashboards.components.filters import render_filters, get_active_filters
from dashboards.components.alerts import render_alert_bar
from dashboards.components.charts import risk_radar, sector_heatmap
from dashboards.dashboard_data import (
    AGENT_SECTOR_MAP,
    load_all_findings,
    load_crucix_signal_stats,
    load_crucix_status,
    discover_agent_names,
)

setup_page("Risk Dashboard", "🛡️")
apply_custom_css()

# Sidebar
render_filters()

findings = load_all_findings()
render_alert_bar(findings)

st.header("Risk Dashboard")
st.caption(
    "Cross-sector risk signals from Crucix (sanctions, conflict, weather, cyber). "
    "Entities tracked by agents are cross-referenced here."
)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

filters = get_active_filters()
crucix = load_crucix_status()
signal_stats = load_crucix_signal_stats()
agent_names = discover_agent_names()

# Apply sector filter
if filters["sectors"]:
    findings = [
        f for f in findings
        if (f.get("sector") or f.get("_agent")) in filters["sectors"]
    ]

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
        "Run: `python -m super_agents crucix sweep --store`"
    )

# ---------------------------------------------------------------------------
# Risk Radar chart
# ---------------------------------------------------------------------------

st.divider()
col_radar, col_heatmap = st.columns(2)

with col_radar:
    st.subheader("Risk Radar")
    # Build risk scores per category from findings
    _categories: dict[str, list[dict]] = {
        "Sanctions": [],
        "Conflict": [],
        "Weather": [],
        "Cyber": [],
        "Regulatory": [],
        "Supply Chain": [],
    }
    sev_weights = {"critical": 100, "high": 70, "medium": 40, "low": 20, "info": 5}

    for f in findings:
        ftype = (f.get("finding_type") or "").lower()
        summary = (f.get("summary") or "").lower()
        title = (f.get("title") or "").lower()
        text = ftype + " " + summary + " " + title
        if "sanction" in text:
            _categories["Sanctions"].append(f)
        elif any(k in text for k in ("conflict", "military", "geopolit")):
            _categories["Conflict"].append(f)
        elif any(k in text for k in ("weather", "fire", "storm", "flood")):
            _categories["Weather"].append(f)
        elif any(k in text for k in ("cyber", "cve", "vulnerab", "malware")):
            _categories["Cyber"].append(f)
        elif any(k in text for k in ("fda", "regulat", "approv", "trial")):
            _categories["Regulatory"].append(f)
        elif any(k in text for k in ("supply", "mineral", "rare earth", "tariff")):
            _categories["Supply Chain"].append(f)

    radar_scores: dict[str, float] = {}
    for cat, cat_findings in _categories.items():
        if not cat_findings:
            radar_scores[cat] = 0.0
        else:
            total = sum(sev_weights.get((f.get("severity") or "info").lower(), 5) for f in cat_findings)
            radar_scores[cat] = min(100.0, float(total))

    fig = risk_radar(radar_scores)
    st.plotly_chart(fig, use_container_width=True)

with col_heatmap:
    st.subheader("Signal Density Heatmap")
    heatmap_data: list[dict] = []
    for f in findings:
        sector = f.get("sector") or f.get("_agent") or "unknown"
        date = (f.get("finding_time") or "")[:10]
        if date:
            heatmap_data.append({"sector": sector, "date": date})

    if heatmap_data:
        fig_hm = sector_heatmap(heatmap_data)
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.info("No finding data for heatmap.")

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
# Signal panels
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Active Signal Monitoring")

p1, p2, p3, p4 = st.columns(4)

with p1:
    st.markdown("### 🚫 Sanctions")
    st.caption("OFAC + OpenSanctions")
    items = _categories["Sanctions"]
    if items:
        for item in items[:5]:
            st.write(f"- {get_severity_icon(item.get('severity', 'info'))} {item.get('summary', '')[:80]}")
    else:
        st.caption("No sanctions signals detected.")

with p2:
    st.markdown("### ⚔️ Conflict")
    st.caption("GDELT + ACLED")
    items = _categories["Conflict"]
    if items:
        for item in items[:5]:
            st.write(f"- {get_severity_icon(item.get('severity', 'info'))} {item.get('summary', '')[:80]}")
    else:
        st.caption("No conflict signals detected.")

with p3:
    st.markdown("### 🌦️ Weather")
    st.caption("NWS + NASA FIRMS")
    items = _categories["Weather"]
    if items:
        for item in items[:5]:
            st.write(f"- {get_severity_icon(item.get('severity', 'info'))} {item.get('summary', '')[:80]}")
    else:
        st.caption("No weather signals detected.")

with p4:
    st.markdown("### 🛡️ Cyber")
    st.caption("CISA KEV + IODA")
    items = _categories["Cyber"]
    if items:
        for item in items[:5]:
            st.write(f"- {get_severity_icon(item.get('severity', 'info'))} {item.get('summary', '')[:80]}")
    else:
        st.caption("No cyber signals detected.")

# ---------------------------------------------------------------------------
# Signal distribution
# ---------------------------------------------------------------------------

st.divider()
cat_counts = {k: len(v) for k, v in _categories.items()}
if any(cat_counts.values()):
    st.subheader("Signal Category Distribution")
    st.bar_chart(pd.Series(cat_counts, name="Signals"))

# ---------------------------------------------------------------------------
# Watchlist
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
        c1.write(f"{get_severity_icon(severity)} **{asset}**")
        c2.caption(agent)
        c3.caption(f.get("finding_time", ""))
else:
    render_empty_state(
        "No action-required findings across the fleet.",
        "python -m super_agents search --verbose",
    )
