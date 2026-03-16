"""Cybersecurity dashboard page for the Phase 1 MVP."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from dashboards.dashboard_data import DASHBOARDS_DIR, load_agent_findings, load_agent_latest_run, load_agent_status

AGENT_NAME = "cybersecurity"
KEV_LATEST_PATH = DASHBOARDS_DIR / "cybersecurity_kev_latest.json"
PATCH_CALENDAR_PATH = DASHBOARDS_DIR / "cybersecurity_patch_calendar.json"
RUN_KEV_COMMAND = (
    "python -m super_agents run --agent cybersecurity --skill threat_landscape "
    "--script fetch_kev_catalog -- --days 30 --limit 50"
)
RUN_CALENDAR_COMMAND = (
    "python -m super_agents run --agent cybersecurity --skill calendar "
    "--script build_patch_calendar -- --window-days 30 --limit 100"
)


def _load_records(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


st.set_page_config(page_title="Cybersecurity", layout="wide")
st.header("Cybersecurity")
st.caption("Phase 1 MVP: CISA KEV feed, watchlist hits, and patch due dates.")

status = load_agent_status(AGENT_NAME)
latest_run = load_agent_latest_run(AGENT_NAME)
findings = load_agent_findings(AGENT_NAME)
kev_records = _load_records(KEV_LATEST_PATH)
calendar_events = _load_records(PATCH_CALENDAR_PATH)

watchlist_only = st.toggle("Watchlist hits only", value=False)
if watchlist_only:
    kev_records = [record for record in kev_records if record.get("watchlist_match")]
    calendar_events = [event for event in calendar_events if event.get("watchlist_match")]
    findings = [finding for finding in findings if finding.get("watchlist_match")]

watchlist_hits = sum(1 for record in kev_records if record.get("watchlist_match"))
critical_hits = sum(1 for record in kev_records if record.get("severity") == "critical")
due_soon = len(calendar_events)
latest_status = status.get("status", "idle") if status else "idle"

metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Agent Status", latest_status)
metric2.metric("KEV Records", len(kev_records))
metric3.metric("Watchlist Hits", watchlist_hits)
metric4.metric("Patch Due Soon", due_soon)

if not kev_records and not calendar_events:
    st.info("No cybersecurity artifacts yet. Run the KEV fetch, then build the patch calendar.")
    st.code(RUN_KEV_COMMAND, language="powershell")
    st.code(RUN_CALENDAR_COMMAND, language="powershell")

if latest_run:
    st.caption(
        f"Latest run: {latest_run.get('task_name', 'N/A')} "
        f"({latest_run.get('status', 'unknown')}) in {latest_run.get('duration_seconds', 0)}s"
    )
if status:
    st.caption(
        f"Current focus: {status.get('current_focus', 'N/A')} | "
        f"Source: {status.get('active_source', 'N/A')}"
    )

tab1, tab2, tab3 = st.tabs(["KEV Feed", "Patch Calendar", "Findings"])

with tab1:
    st.subheader("Known Exploited Vulnerabilities")
    st.caption(f"Critical rows in the current view: {critical_hits}")
    if kev_records:
        table_rows = []
        for record in kev_records[:200]:
            table_rows.append(
                {
                    "cve_id": record.get("cve_id", ""),
                    "vendor": record.get("vendor", ""),
                    "product": record.get("product", ""),
                    "date_added": record.get("date_added", ""),
                    "due_date": record.get("due_date", ""),
                    "severity": record.get("severity", ""),
                    "ransomware": record.get("known_ransomware_campaign_use", ""),
                    "watchlist_match": record.get("watchlist_match", False),
                }
            )
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No KEV records loaded yet.")

with tab2:
    st.subheader("Patch Calendar")
    if calendar_events:
        table_rows = []
        for event in calendar_events[:200]:
            table_rows.append(
                {
                    "date": event.get("date", ""),
                    "cve_id": event.get("cve_id", ""),
                    "asset": event.get("asset", ""),
                    "severity": event.get("severity", ""),
                    "watchlist_match": event.get("watchlist_match", False),
                    "detail": event.get("detail", ""),
                }
            )
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No patch calendar events yet. Run build_patch_calendar after the KEV fetch.")

with tab3:
    st.subheader("Latest Findings")
    if findings:
        for finding in findings[:25]:
            st.write(f"[{finding.get('severity', 'info')}] {finding.get('summary', '')}")
            st.caption(
                f"CVE: {finding.get('cve_id', 'N/A')} | "
                f"Due: {finding.get('due_date', 'N/A')} | "
                f"Source: {finding.get('source_url', 'N/A')}"
            )
    else:
        st.info("No findings artifact yet. Run fetch_kev_catalog to generate it.")
