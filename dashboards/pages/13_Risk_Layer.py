"""Global Risk Layer dashboard."""

import streamlit as st
import pandas as pd
from dashboards.components.risk_badge import render_risk_badge, get_risk_context_mock

st.set_page_config(page_title="Global Risk Layer", layout="wide")

st.header("Global Risk Layer — Unified Signal Dashboard")
st.markdown("""
Monitor cross-sector risk signals including Sanctions, Conflict, Weather, and Cyber alerts. 
Any entity tracked across the fleet is cross-referenced here.
""")

# Sidebar settings
st.sidebar.header("Settings")
refresh_rate = st.sidebar.slider("Auto-refresh (minutes)", 5, 60, 30)
st.sidebar.caption(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Top Row: Search & Quick Context
search_col1, search_col2 = st.columns([2, 1])

with search_col1:
    search_query = st.text_input("Entity Search", placeholder="Type a company, vessel, or country name...")
    if search_query:
        risk = get_risk_context_mock(search_query, "Global")
        st.subheader(f"Risk Context: {search_query}")
        
        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        col_res1.metric("Sanctions Hit", "YES" if risk["sanctions_hit"] else "NO")
        col_res2.metric("Conflict Proximity", "HIGH" if risk["conflict_nearby"] else "LOW")
        col_res3.metric("Cyber Exposure", "MEDIUM" if risk["cyber_alert"] else "LOW")
        col_res4.metric("Weather Impact", "NONE" if not risk["weather_hazard"] else "HIGH")
        
        st.info(f"**Detail**: {risk['description']}")
    else:
        st.info("Enter an entity name above to see its real-time risk context.")

with search_col2:
    st.subheader("Global Risk Summary")
    # Mock summary stats
    st.metric("Critical Sanctions Hits", 12, delta="+2 this week")
    st.metric("Active Conflict Events (24h)", 48, delta="-5")

st.divider()

# Main Signal Panels
st.subheader("Active Signal Monitoring")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 🚫 Sanctions")
    st.caption("OFAC + OpenSanctions")
    # Placeholder for real list
    mock_sanctions = [
        {"entity": "PJSC Rosneft", "country": "RU", "severity": "critical"},
        {"entity": "Mahan Air", "country": "IR", "severity": "critical"},
    ]
    for item in mock_sanctions:
        st.write(f"- {item['entity']} ({item['country']})")

with col2:
    st.markdown("### ⚔️ Conflict")
    st.caption("GDELT + ReliefWeb")
    mock_conflicts = [
        {"event": "Red Sea Shipping Strike", "region": "Yemen", "severity": "high"},
        {"event": "Sudan Supply Chain Disruption", "region": "Sudan", "severity": "high"},
    ]
    for item in mock_conflicts:
        st.write(f"- {item['event']}")

with col3:
    st.markdown("### 🌦️ Weather")
    st.caption("NWS + NASA FIRMS")
    mock_weather = [
        {"hazard": "California Wildfires", "severity": "medium"},
        {"hazard": "Taiwan Typhoon Warning", "severity": "medium"},
    ]
    for item in mock_weather:
        st.write(f"- {item['hazard']}")

with col4:
    st.markdown("### 🛡️ Cyber")
    st.caption("CISA KEV + IODA")
    mock_cyber = [
        {"alert": "Critical Fortinet Vulnerability", "severity": "high"},
        {"alert": "Pakistan BGP Hijack", "severity": "medium"},
    ]
    for item in mock_cyber:
        st.write(f"- {item['alert']}")

st.divider()

# Watchlist Table
st.subheader("Watchlist Entities with Active Risk Signals")
# Sample data for the table
watchlist_data = [
    {"Entity": "Gazprom", "Country": "RU", "Risk Level": "CRITICAL", "Primary Signal": "Sanctions", "Last Checked": "2 mins ago"},
    {"Entity": "Ever Given (Vessel)", "Country": "Global", "Risk Level": "MEDIUM", "Primary Signal": "Maritime/Weather", "Last Checked": "14 mins ago"},
    {"Entity": "TSMC Fab 1", "Country": "TW", "Risk Level": "HIGH", "Primary Signal": "Geopolitical/Cyber", "Last Checked": "1 hr ago"},
    {"Entity": "Houthi Militia", "Country": "YE", "Risk Level": "CRITICAL", "Primary Signal": "Conflict/Sanctions", "Last Checked": "5 mins ago"},
]

df = pd.DataFrame(watchlist_data)

# Show table with badges (Streamlit st.dataframe doesn't easily support the custom badge HTML, 
# so we use a loop for a list-like view or st.table for simple display)
for index, row in df.iterrows():
    c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
    with c1:
        render_risk_badge(row["Entity"], row["Country"])
        st.write(f"**{row['Entity']}**")
    with c2:
        st.write(row["Country"])
    with c3:
        st.write(row["Primary Signal"])
    with c4:
        st.write(f"Updated: {row['Last Checked']}")
