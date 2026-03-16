"""Crucix Data Hub — Live intelligence feeds, signal routing, and source health."""

from __future__ import annotations

import streamlit as st

from dashboards.dashboard_data import (
    AGENT_SECTOR_MAP,
    discover_runnable_agents,
    get_agent_sector,
    load_crucix_signal_stats,
    load_crucix_source_map,
    load_crucix_status,
    load_latest_briefing_summary,
)

st.set_page_config(page_title="Crucix Data Hub", layout="wide")
st.header("Crucix Data Hub")
st.caption(
    "Real-time intelligence from 27 OSINT, financial, and geopolitical data sources. "
    "Crucix sweeps the world every 15 minutes and routes signals to matching agents."
)

# ---------------------------------------------------------------------------
# Status bar
# ---------------------------------------------------------------------------

crucix = load_crucix_status()
briefing = load_latest_briefing_summary()
signal_stats = load_crucix_signal_stats()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Status", "Installed" if crucix["installed"] else "Not Installed")
col2.metric("Latest Sweep", "Available" if crucix["latest_briefing_exists"] else "None")
col3.metric(
    "Sources OK",
    f"{briefing['ok_sources']}/{briefing['total_sources']}" if briefing else "N/A",
)
col4.metric("Stored Signals", signal_stats.get("total_signals", 0))
col5.metric("Signal DB", "Active" if crucix["signals_db_exists"] else "Empty")

if not crucix["cloned"]:
    st.warning(
        "Crucix is not installed. Run `python -m super_agents crucix setup` to clone and install."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Latest sweep results
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Latest Sweep")

if briefing:
    st.success(
        f"Sweep at {briefing['timestamp']} - "
        f"{briefing['ok_sources']} sources OK, {briefing['error_sources']} errors"
    )

    sweep_left, sweep_right = st.columns(2)
    with sweep_left:
        st.markdown("**Active Sources:**")
        for source_name in sorted(briefing.get("ok_source_names", [])):
            st.markdown(f"- ✅ {source_name}")

    with sweep_right:
        if briefing.get("error_source_names"):
            st.markdown("**Failed Sources:**")
            for source_name in sorted(briefing["error_source_names"]):
                st.markdown(f"- ❌ {source_name}")
        else:
            st.info("All sources healthy.")
else:
    st.info(
        "No sweep data yet. Run `python -m super_agents crucix sweep` to perform the first sweep."
    )

# ---------------------------------------------------------------------------
# Signal store
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Signal Store")

if signal_stats.get("total_signals", 0) > 0:
    stats_left, stats_right = st.columns(2)

    with stats_left:
        st.metric("Total Signals", signal_stats["total_signals"])
        st.metric("Processed", signal_stats.get("processed", 0))
        st.metric("Unprocessed", signal_stats.get("unprocessed", 0))

        unique_sources = signal_stats.get("unique_sources", [])
        if unique_sources:
            st.markdown(f"**Sources:** {', '.join(sorted(unique_sources))}")

    with stats_right:
        st.markdown("**Top Topics:**")
        top_topics = signal_stats.get("top_topics", {})
        if top_topics:
            for topic, count in list(top_topics.items())[:15]:
                st.markdown(f"- {topic}: **{count}**")
        else:
            st.caption("No topic data available.")
else:
    st.info(
        "Signal store is empty. Run `python -m super_agents crucix sweep --store` to persist signals."
    )

# ---------------------------------------------------------------------------
# Source-to-Sector map (the 27 Crucix sources)
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Source-to-Sector Routing Map")
st.caption("How each of Crucix's 27 data sources maps to your agent sectors.")

source_map = load_crucix_source_map()

if source_map:
    # Group sources by tier
    tiers = {
        "Tier 1 - Core OSINT & Geopolitical": [
            "GDELT", "OpenSky", "FIRMS", "Maritime", "Safecast",
            "ACLED", "ReliefWeb", "WHO", "OFAC", "OpenSanctions", "ADS-B",
        ],
        "Tier 2 - Economic & Financial": [
            "FRED", "Treasury", "BLS", "EIA", "GSCPI", "USAspending", "Comtrade",
        ],
        "Tier 3 - Weather, Environment, Social": [
            "NOAA", "EPA", "Patents", "Bluesky", "Reddit", "Telegram", "KiwiSDR",
        ],
        "Tier 4 - Space & Satellites": ["Space"],
        "Tier 5 - Live Market Data": ["yfinance"],
    }

    for tier_name, tier_sources in tiers.items():
        with st.expander(f"{tier_name} ({len(tier_sources)} sources)"):
            for source_name in tier_sources:
                info = source_map.get(source_name, {})
                if not info:
                    continue

                sectors = info.get("sectors", ())
                confidence = info.get("confidence", "secondary")
                description = info.get("description", "")

                sector_icons = ""
                if sectors:
                    sector_icons = " ".join(
                        get_agent_sector(s).get("icon", "📦") for s in sectors
                    )
                else:
                    sector_icons = "🌐 ALL"

                conf_badge = {
                    "primary": "🟢",
                    "secondary": "🟡",
                    "sponsor": "🟠",
                }.get(confidence, "⚪")

                st.markdown(
                    f"**{source_name}** {conf_badge} {sector_icons}\n\n"
                    f"  {description}"
                )
                if sectors:
                    st.caption(f"Sectors: {', '.join(sectors)}")
                else:
                    st.caption("Broadcast to all agents")

    # Agent coverage heatmap
    st.divider()
    st.subheader("Agent Coverage")
    st.caption("Number of Crucix sources feeding each agent sector.")

    agents = discover_runnable_agents()
    agent_names = {a["name"] for a in agents}

    coverage: dict[str, list[str]] = {}
    for source_name, info in source_map.items():
        sectors = info.get("sectors", ())
        if not sectors:
            # Broadcast sources cover everyone
            for agent_name in agent_names:
                coverage.setdefault(agent_name, []).append(source_name)
        else:
            for sector in sectors:
                if sector in agent_names:
                    coverage.setdefault(sector, []).append(source_name)

    coverage_cols = st.columns(min(5, len(coverage) or 1))
    for idx, (agent_name, sources) in enumerate(sorted(coverage.items(), key=lambda x: -len(x[1]))):
        col = coverage_cols[idx % len(coverage_cols)]
        sector = get_agent_sector(agent_name)
        with col:
            st.metric(
                f"{sector['icon']} {agent_name}",
                f"{len(sources)} sources",
            )

else:
    st.info("Source map not available. Ensure `super_agents.integrations.crucix` is importable.")

# ---------------------------------------------------------------------------
# CLI reference
# ---------------------------------------------------------------------------

st.divider()
st.subheader("CLI Commands")
st.code(
    """# Check Crucix status
python -m super_agents crucix status

# Install Crucix (clone + npm install)
python -m super_agents crucix setup

# Run a sweep and parse signals
python -m super_agents crucix sweep

# Sweep and persist to SQLite
python -m super_agents crucix sweep --store

# Dry-run signal routing
python -m super_agents crucix route

# Query stored signals
python -m super_agents crucix signals --topic maritime --limit 10

# List all source mappings
python -m super_agents crucix sources""",
    language="bash",
)
