"""Super Agents — Command Center Home Page.

Launch: streamlit run dashboards/app.py
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import streamlit as st

from dashboards.dashboard_data import (
    AGENT_SECTOR_MAP,
    discover_runnable_agents,
    discover_simulation_results,
    group_agents_by_sector,
    load_all_findings,
    load_all_runs,
    load_crucix_signal_stats,
    load_crucix_status,
    load_latest_briefing_summary,
)
from dashboards.components.theme import (
    SEVERITY_COLORS,
    get_severity_icon,
    get_status_icon,
    setup_page,
)
from dashboards.components.filters import render_filters, get_active_filters
from dashboards.components.alerts import render_alert_bar
from dashboards.components.charts import signal_sankey, run_timeline
from dashboards.components.cards import FindingCard

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

setup_page("Command Center", "🔭")

# Sidebar filters
render_filters(show_agent_filter=False)

st.title("🔭 Super Agents — Command Center")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

agents = discover_runnable_agents()
runs = load_all_runs()
findings = load_all_findings()
crucix = load_crucix_status()
signal_stats = load_crucix_signal_stats()
briefing = load_latest_briefing_summary()
scenario_results = discover_simulation_results()
filters = get_active_filters()

# Apply time filter to runs and findings
_since = filters.get("since")
if _since:
    _since_str = _since.isoformat()
    runs_today = [r for r in runs if (r.get("started_at") or "") >= _since_str]
    findings_window = [f for f in findings if (f.get("finding_time") or "") >= _since_str]
else:
    runs_today = runs
    findings_window = findings

critical_findings = [f for f in findings_window if (f.get("severity") or "").lower() == "critical"]
high_findings = [f for f in findings_window if (f.get("severity") or "").lower() == "high"]
active_agents = [a for a in agents]  # all discovered agents are "active"

# ---------------------------------------------------------------------------
# Alert bar (top of page)
# ---------------------------------------------------------------------------

render_alert_bar(findings)

# ---------------------------------------------------------------------------
# Row 1: KPI Metric Cards
# ---------------------------------------------------------------------------

st.markdown("### Key Metrics")
c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Agents Active",
    len(active_agents),
    help="Total discovered runnable agents",
)
c2.metric(
    "Runs (window)",
    len(runs_today),
    help=f"Runs in selected time window ({filters['time_preset']})",
)
c3.metric(
    "Findings (window)",
    len(findings_window),
    delta=f"⚠ {len(critical_findings)} critical" if critical_findings else None,
    delta_color="inverse" if critical_findings else "normal",
)
c4.metric(
    "Critical Alerts",
    len(critical_findings),
    help="Critical severity findings in time window",
)

crucix_label = "Active" if crucix.get("installed") else "Setup Needed"
crucix_sources = signal_stats.get("total_signals", 0)
c5.metric(
    f"Crucix: {crucix_label}",
    f"{crucix_sources} signals",
    help="Total signals in Crucix signal store",
)

st.divider()

# ---------------------------------------------------------------------------
# Row 2: Recent Alerts (left) + Signal Flow mini-chart (right)
# ---------------------------------------------------------------------------

col_alerts, col_signal = st.columns([1, 1])

with col_alerts:
    st.markdown("#### 🚨 Recent Alerts")
    alert_findings = [
        f for f in findings_window
        if (f.get("severity") or "info").lower() in ("critical", "high")
    ][:8]

    if alert_findings:
        for f in alert_findings[:5]:
            FindingCard(f, expandable=False)
        if len(alert_findings) > 5:
            st.caption(f"+ {len(alert_findings) - 5} more — see Findings Board")
    else:
        st.info("✅ No critical or high alerts in the selected time window.")

with col_signal:
    st.markdown("#### 📡 Signal Flow (24h)")
    # Build signal data from briefing for the Sankey
    briefing_signals: list[dict[str, Any]] = []
    if briefing:
        for src_name in briefing.get("ok_source_names", []):
            briefing_signals.append({
                "source": src_name,
                "topic": "briefing",
                "sector": "unknown",
            })

    # Try to enrich with signal stats topics
    top_topics = signal_stats.get("top_topics", {})
    if isinstance(top_topics, dict) and top_topics:
        # Build simplified signals from topic stats
        briefing_signals = []
        for topic, count in list(top_topics.items())[:10]:
            briefing_signals.append({
                "source": "crucix",
                "topic": topic,
                "sector": "unknown",
                "count": count,
            })

    if briefing_signals:
        from dashboards.components.charts import signal_sankey
        fig = signal_sankey(briefing_signals)
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No signal flow data. Run a Crucix briefing to populate.")

st.divider()

# ---------------------------------------------------------------------------
# Row 3: Sector Status Grid
# ---------------------------------------------------------------------------

st.markdown("#### 🗺 Sector Status Grid")

sector_groups = group_agents_by_sector(agents)
all_sector_names = list(AGENT_SECTOR_MAP.keys())

# Build per-sector health: count findings in window
_sector_finding_counts: dict[str, int] = {}
for f in findings_window:
    s = f.get("sector") or f.get("_agent") or "unknown"
    _sector_finding_counts[s] = _sector_finding_counts.get(s, 0) + 1

_sector_critical: dict[str, int] = {}
for f in critical_findings:
    s = f.get("sector") or f.get("_agent") or "unknown"
    _sector_critical[s] = _sector_critical.get(s, 0) + 1

grid_agents = {a["name"]: a for a in agents}
cols_per_row = 4
sector_cols = st.columns(cols_per_row)

for idx, sector_name in enumerate(all_sector_names):
    meta = AGENT_SECTOR_MAP[sector_name]
    icon = meta["icon"]
    color = meta["color"]
    label = sector_name.replace("_", " ").title()

    crit_count = _sector_critical.get(sector_name, 0)
    find_count = _sector_finding_counts.get(sector_name, 0)
    has_agent = sector_name in grid_agents

    if crit_count > 0:
        status_dot = "🔴"
        status_text = f"CRITICAL ({crit_count})"
        bg = f"{SEVERITY_COLORS['critical']}22"
    elif find_count > 0:
        status_dot = "🟡"
        status_text = f"{find_count} findings"
        bg = f"{SEVERITY_COLORS['medium']}22"
    elif has_agent:
        status_dot = "🟢"
        status_text = "OK"
        bg = f"{color}22"
    else:
        status_dot = "⚪"
        status_text = "No agent"
        bg = "rgba(255,255,255,0.03)"

    html = (
        f'<div style="background:{bg};border:1px solid {color}44;border-radius:8px;'
        f'padding:10px 12px;margin-bottom:8px;min-height:70px;">'
        f'<div style="font-size:1.2rem">{icon}</div>'
        f'<div style="font-weight:600;font-size:0.85rem">{label}</div>'
        f'<div style="font-size:0.78rem;color:#bbb">{status_dot} {status_text}</div>'
        f'</div>'
    )
    sector_cols[idx % cols_per_row].markdown(html, unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# Row 4: Latest Runs (left) + Upcoming Catalysts (right)
# ---------------------------------------------------------------------------

col_runs, col_catalysts = st.columns([1, 1])

with col_runs:
    st.markdown("#### 🏃 Latest Runs")
    if runs_today:
        table_rows = []
        for r in runs_today[:10]:
            status = (r.get("status") or "unknown").lower()
            s_icon = get_status_icon(status)
            started = (r.get("started_at") or "")[:16].replace("T", " ")
            table_rows.append({
                "Agent": r.get("agent", r.get("agent_name", "—")),
                "Skill": r.get("skill", r.get("script", "—")),
                "Status": f"{s_icon} {status.title()}",
                "Started": started,
            })
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No runs in the selected time window.")

with col_catalysts:
    st.markdown("#### 📅 Upcoming Catalysts")
    # Scan for calendar events from scenarios/findings
    upcoming: list[dict[str, Any]] = []
    today = datetime.utcnow().date()
    for r in scenario_results[:5]:
        upcoming.append({
            "Date": (r.get("completed_at") or "")[:10],
            "Event": r.get("scenario", "Simulation"),
            "Sector": "simulation",
        })

    if upcoming:
        st.dataframe(upcoming, use_container_width=True, hide_index=True)
    else:
        st.info("No upcoming catalysts. Run calendar agents to populate.")

# ---------------------------------------------------------------------------
# Sidebar quick status
# ---------------------------------------------------------------------------

st.sidebar.divider()
st.sidebar.subheader("Quick Status")

if crucix.get("installed"):
    st.sidebar.success("Crucix: Installed")
else:
    st.sidebar.warning("Crucix: Not installed")

action_count = sum(1 for f in findings if f.get("action_required"))
st.sidebar.caption(
    f"Agents: {len(agents)} | Runs: {len(runs)} | Action items: {action_count}"
)
