"""Cybersecurity Intelligence — KEV feed, watchlist hits, and patch calendar."""

from __future__ import annotations

import streamlit as st
import pandas as pd

from dashboards.dashboard_data import (
    DASHBOARDS_DIR,
    _safe_load_json,
    load_agent_findings,
    load_agent_latest_run,
    load_agent_status,
    load_all_findings,
)
from dashboards.components.theme import setup_page, apply_custom_css, get_severity_icon
from dashboards.components.filters import render_filters
from dashboards.components.alerts import render_alert_bar

AGENT_NAME = "cybersecurity"
KEV_LATEST_PATH = DASHBOARDS_DIR / "cybersecurity_kev_latest.json"
PATCH_CALENDAR_PATH = DASHBOARDS_DIR / "cybersecurity_patch_calendar.json"


def _load_records(path) -> list[dict]:
    data = _safe_load_json(path)
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


setup_page("Cybersecurity", "🔒")
apply_custom_css()

render_filters(show_agent_filter=False)

findings_all = load_all_findings()
render_alert_bar(findings_all)

st.header("Cybersecurity Intelligence")
st.caption("CISA KEV feed, watchlist hits, and patch due dates.")

status = load_agent_status(AGENT_NAME)
latest_run = load_agent_latest_run(AGENT_NAME)
findings = load_agent_findings(AGENT_NAME)
kev_records = _load_records(KEV_LATEST_PATH)
calendar_events = _load_records(PATCH_CALENDAR_PATH)

watchlist_only = st.toggle("Watchlist hits only", value=False)
if watchlist_only:
    kev_records = [r for r in kev_records if r.get("watchlist_match")]
    calendar_events = [e for e in calendar_events if e.get("watchlist_match")]
    findings = [f for f in findings if f.get("watchlist_match")]

# ---------------------------------------------------------------------------
# Visualizations
# ---------------------------------------------------------------------------

st.divider()
vcol1, vcol2 = st.columns(2)

with vcol1:
    st.subheader("KEV Severity Distribution")
    if kev_records:
        sev_counts = pd.Series(
            [r.get("severity", "unknown") for r in kev_records]
        ).value_counts()
        st.bar_chart(sev_counts)
    else:
        st.info("No KEV records for severity chart.")

with vcol2:
    st.subheader("Patch Timeline")
    if calendar_events:
        cal_df = pd.DataFrame(calendar_events)
        if "date" in cal_df.columns:
            cal_df["date"] = pd.to_datetime(cal_df["date"])
            timeline = cal_df.set_index("date").resample("D").size()
            st.line_chart(timeline)
        else:
            st.info("Insufficient date data for patch timeline.")
    else:
        st.info("No calendar events for patch timeline.")

st.divider()

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

watchlist_hits = sum(1 for r in kev_records if r.get("watchlist_match"))
critical_hits = sum(1 for r in kev_records if r.get("severity") == "critical")
due_soon = len(calendar_events)
latest_status = status.get("status", "idle") if status else "idle"

m1, m2, m3, m4 = st.columns(4)
m1.metric("Agent Status", latest_status)
m2.metric("KEV Records", len(kev_records))
m3.metric("Watchlist Hits", watchlist_hits)
m4.metric("Patch Due Soon", due_soon)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab1, tab2, tab3 = st.tabs(["KEV Feed", "Patch Calendar", "Findings"])

with tab1:
    st.subheader("Known Exploited Vulnerabilities")
    if kev_records:
        st.dataframe(kev_records[:200], use_container_width=True, hide_index=True)
    else:
        st.info("No KEV records loaded yet.")

with tab2:
    st.subheader("Patch Calendar")
    if calendar_events:
        st.dataframe(calendar_events[:200], use_container_width=True, hide_index=True)
    else:
        st.info("No patch calendar events yet.")

with tab3:
    st.subheader("Latest Findings")
    if findings:
        for finding in findings[:25]:
            icon = get_severity_icon(finding.get("severity", "info"))
            st.write(f"{icon} {finding.get('summary', '')}")
            st.caption(
                f"CVE: {finding.get('cve_id', 'N/A')} | "
                f"Source: {finding.get('source_url', 'N/A')}"
            )
    else:
        st.info("No findings artifact yet.")
