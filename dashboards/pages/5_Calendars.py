"""Calendars & Scoreboards — Forward-looking views."""

import json
from pathlib import Path

import streamlit as st

from dashboards.dashboard_data import DASHBOARDS_DIR, load_calendar_events

st.set_page_config(page_title="Calendars", layout="wide")
st.header("Calendars & Scoreboards")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Catalyst Calendar", "Release Calendar", "Program Calendar", "Financial Runway"]
)

with tab1:
    st.subheader("Biotech Catalyst Calendar")
    events = load_calendar_events("*catalyst_calendar*.json")
    if events:
        for event in events[:30]:
            st.write(
                f"**{event.get('date', 'TBD')}** — {event.get('ticker', '')} "
                f"| {event.get('product', '')} | {event.get('catalyst_type', '')} "
                f"| {event.get('official_vs_sponsor', '')}"
            )
    else:
        st.info("No catalyst calendar data. Run biotech daily update.")

with tab2:
    st.subheader("Gaming Release Calendar")
    events = load_calendar_events("*release_calendar*.json")
    if events:
        for event in events[:30]:
            st.write(
                f"**{event.get('date', 'TBD')}** — {event.get('title', '')} "
                f"| {event.get('event_type', '')} | {event.get('platform', '')}"
            )
    else:
        st.info("No release calendar data. Run gaming daily update.")

with tab3:
    st.subheader("Aerospace Program Calendar")
    events = load_calendar_events("*program_calendar*.json")
    if events:
        for event in events[:30]:
            st.write(
                f"**{event.get('date', 'TBD')}** — {event.get('system', '')} "
                f"| {event.get('milestone_type', '')} | {event.get('agency', '')}"
            )
    else:
        st.info("No program calendar data. Run aerospace daily update.")

with tab4:
    st.subheader("Financial Runway — All Sectors")
    runway_files = list(DASHBOARDS_DIR.glob("*runway*.json")) + list(
        Path("data/processed/financials").glob("master_runway.csv")
    )
    if runway_files:
        for path in runway_files:
            if path.suffix == ".json":
                st.json(json.loads(path.read_text(encoding="utf-8")))
            elif path.suffix == ".csv":
                import pandas as pd

                dataframe = pd.read_csv(path)
                st.dataframe(dataframe, use_container_width=True)
    else:
        st.info("No runway data. Run financial monitor workflows.")
