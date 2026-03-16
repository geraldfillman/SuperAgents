"""Calendars & Scoreboards — Forward-looking views across all sectors."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboards.dashboard_data import DASHBOARDS_DIR, load_calendar_events
from dashboards.components.theme import setup_page, apply_custom_css
from dashboards.components.empty_state import render_empty_state

setup_page("Calendars", "\U0001f4c5")
apply_custom_css()

st.header("Calendars & Scoreboards")

# ---------------------------------------------------------------------------
# Aggregate all calendar data for the overview chart
# ---------------------------------------------------------------------------

catalyst_events = load_calendar_events("*catalyst_calendar*.json")
release_events = load_calendar_events("*release_calendar*.json")
program_events = load_calendar_events("*program_calendar*.json")
energy_events = load_calendar_events("*energy_calendar*.json")

all_events = (
    [dict(e, _type="Catalyst") for e in catalyst_events]
    + [dict(e, _type="Release") for e in release_events]
    + [dict(e, _type="Program") for e in program_events]
    + [dict(e, _type="Energy") for e in energy_events]
)

# ---------------------------------------------------------------------------
# Overview metrics & timeline
# ---------------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)
col1.metric("Catalyst Events", len(catalyst_events))
col2.metric("Release Events", len(release_events))
col3.metric("Program Events", len(program_events))
col4.metric("Total Events", len(all_events))

if all_events:
    st.divider()
    st.subheader("Event Timeline (All Calendars)")
    events_df = pd.DataFrame(all_events)
    if "date" in events_df.columns:
        events_df["date"] = pd.to_datetime(events_df["date"], errors="coerce")
        events_df = events_df.dropna(subset=["date"])
        if not events_df.empty:
            timeline = events_df.groupby([events_df["date"].dt.date, "_type"]).size().unstack(fill_value=0)
            st.bar_chart(timeline)
            st.caption("Events per day across all calendar types")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

st.divider()
tab1, tab2, tab3, tab4 = st.tabs(
    ["Catalyst Calendar", "Release Calendar", "Program Calendar", "Financial Runway"]
)

with tab1:
    st.subheader("Biotech Catalyst Calendar")
    if catalyst_events:
        for event in catalyst_events[:30]:
            st.write(
                f"**{event.get('date', 'TBD')}** \u2014 {event.get('ticker', '')} "
                f"| {event.get('product', '')} | {event.get('catalyst_type', '')} "
                f"| {event.get('official_vs_sponsor', '')}"
            )
    else:
        render_empty_state(
            "No catalyst calendar data.",
            "python -m super_agents run --agent biotech --skill daily_update --verbose",
        )

with tab2:
    st.subheader("Gaming Release Calendar")
    if release_events:
        for event in release_events[:30]:
            st.write(
                f"**{event.get('date', 'TBD')}** \u2014 {event.get('title', '')} "
                f"| {event.get('event_type', '')} | {event.get('platform', '')}"
            )
    else:
        render_empty_state(
            "No release calendar data.",
            "python -m super_agents run --agent gaming --skill daily_update --verbose",
        )

with tab3:
    st.subheader("Aerospace Program Calendar")
    if program_events:
        for event in program_events[:30]:
            st.write(
                f"**{event.get('date', 'TBD')}** \u2014 {event.get('system', '')} "
                f"| {event.get('milestone_type', '')} | {event.get('agency', '')}"
            )
    else:
        render_empty_state(
            "No program calendar data.",
            "python -m super_agents run --agent aerospace --skill daily_update --verbose",
        )

with tab4:
    st.subheader("Financial Runway \u2014 All Sectors")
    runway_files = list(DASHBOARDS_DIR.glob("*runway*.json")) + list(
        Path("data/processed/financials").glob("master_runway.csv")
    )
    if runway_files:
        for path in runway_files:
            if path.suffix == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                st.json(data)
            elif path.suffix == ".csv":
                dataframe = pd.read_csv(path)
                st.dataframe(dataframe, use_container_width=True)
    else:
        render_empty_state(
            "No runway data.",
            "python -m super_agents run --agent fintech --skill financial_monitor --verbose",
        )
