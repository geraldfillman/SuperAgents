"""Card components for agents, findings, signals, and simulations."""

from __future__ import annotations

from typing import Any

import streamlit as st

from dashboards.dashboard_data import AGENT_SECTOR_MAP
from dashboards.components.theme import (
    get_severity_color,
    get_severity_icon,
    get_status_icon,
    SEVERITY_COLORS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _border_style(color: str) -> str:
    return (
        f"border-left: 4px solid {color}; "
        "background: rgba(255,255,255,0.04); "
        "border-radius: 6px; "
        "padding: 12px 16px; "
        "margin-bottom: 10px;"
    )


def _badge(text: str, color: str, text_color: str = "#fff") -> str:
    return (
        f'<span style="background:{color};color:{text_color};'
        f'padding:2px 8px;border-radius:12px;font-size:0.78rem;'
        f'font-weight:600;margin-right:4px;">{text}</span>'
    )


def _sector_meta(agent_name: str) -> dict[str, Any]:
    return AGENT_SECTOR_MAP.get(agent_name, {
        "sector": agent_name,
        "icon": "📦",
        "color": "#BDC3C7",
    })


# ---------------------------------------------------------------------------
# AgentCard
# ---------------------------------------------------------------------------

def AgentCard(agent_data: dict[str, Any]) -> None:
    """Render a styled card for one agent.

    Parameters
    ----------
    agent_data:
        Dict from ``discover_runnable_agents()``, optionally enriched with
        ``status`` and ``last_run`` keys.
    """
    name: str = agent_data.get("name", "unknown")
    label: str = agent_data.get("label", name.replace("_", " ").title())
    description: str = agent_data.get("description", "")
    skill_count: int = agent_data.get("skill_count", 0)
    last_run: str = agent_data.get("last_run", "Never")
    status: str = (agent_data.get("status") or "idle").lower()

    meta = _sector_meta(name)
    border_color: str = meta.get("color", "#BDC3C7")
    icon: str = meta.get("icon", "📦")
    status_icon: str = get_status_icon(status)

    html = (
        f'<div style="{_border_style(border_color)}">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
        f'<span style="font-size:1.4rem">{icon}</span>'
        f'<strong style="font-size:1rem">{label}</strong>'
        f'{_badge(status.title(), border_color)}'
        f'</div>'
        f'<div style="font-size:0.85rem;color:#aaa;margin-bottom:4px;">{description}</div>'
        f'<div style="font-size:0.8rem;display:flex;gap:16px;">'
        f'<span>{status_icon} {status.title()}</span>'
        f'<span>🛠 {skill_count} skills</span>'
        f'<span>🕐 {last_run}</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# FindingCard
# ---------------------------------------------------------------------------

def FindingCard(finding_data: dict[str, Any], *, expandable: bool = True) -> None:
    """Render a styled card for one finding.

    Parameters
    ----------
    finding_data:
        Dict with keys: ``title``, ``severity``, ``sector`` / ``_agent``,
        ``finding_time``, optional ``summary`` / ``details``.
    expandable:
        If True, wrap the details in an st.expander.
    """
    title: str = finding_data.get("title", "Untitled Finding")
    severity: str = (finding_data.get("severity") or "info").lower()
    sector: str = finding_data.get("sector") or finding_data.get("_agent") or "unknown"
    timestamp: str = finding_data.get("finding_time", "")
    summary: str = finding_data.get("summary", finding_data.get("details", ""))

    sev_color = get_severity_color(severity)
    sev_icon = get_severity_icon(severity)
    sector_meta = _sector_meta(sector)
    sector_color = sector_meta.get("color", "#BDC3C7")
    sector_icon = sector_meta.get("icon", "📦")

    ts_display = timestamp[:16].replace("T", " ") if timestamp else "—"

    html = (
        f'<div style="{_border_style(sev_color)}">'
        f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">'
        f'{_badge(f"{sev_icon} {severity.upper()}", sev_color)}'
        f'{_badge(f"{sector_icon} {sector.replace(chr(95), " ").title()}", sector_color)}'
        f'<span style="font-size:0.78rem;color:#888;margin-left:auto;">{ts_display}</span>'
        f'</div>'
        f'<div style="font-weight:600;margin-top:6px;">{title}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    if expandable and summary:
        with st.expander("Details", expanded=False):
            st.markdown(summary)


# ---------------------------------------------------------------------------
# SignalCard
# ---------------------------------------------------------------------------

def SignalCard(signal_data: dict[str, Any]) -> None:
    """Render a styled card for one Crucix signal.

    Parameters
    ----------
    signal_data:
        Dict with keys: ``source``, ``topic``, ``sector``, ``confidence``,
        optional ``summary``, ``url``.
    """
    source: str = signal_data.get("source", "unknown")
    topic: str = signal_data.get("topic", "—")
    sector: str = signal_data.get("sector", "unknown")
    confidence: float = float(signal_data.get("confidence", 0.0))
    summary: str = signal_data.get("summary", "")
    url: str = signal_data.get("url", "")

    sector_meta = _sector_meta(sector)
    border_color = sector_meta.get("color", "#BDC3C7")
    sector_icon = sector_meta.get("icon", "📦")

    conf_pct = int(confidence * 100) if confidence <= 1.0 else int(confidence)
    conf_color = (
        "#2ECC71" if conf_pct >= 80
        else "#F1C40F" if conf_pct >= 50
        else "#E74C3C"
    )

    source_label = source.replace("_", " ").title()
    topic_display = topic[:80] + "…" if len(topic) > 80 else topic

    html = (
        f'<div style="{_border_style(border_color)}">'
        f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">'
        f'<span style="font-size:0.85rem;font-weight:600;">📡 {source_label}</span>'
        f'{_badge(f"{sector_icon} {sector.replace(chr(95), " ").title()}", border_color)}'
        f'{_badge(f"{conf_pct}% conf", conf_color)}'
        f'</div>'
        f'<div style="margin-top:6px;font-size:0.9rem;">{topic_display}</div>'
    )
    if summary:
        html += f'<div style="font-size:0.8rem;color:#aaa;margin-top:4px;">{summary[:120]}…</div>'
    if url:
        html += f'<div style="margin-top:4px;"><a href="{url}" target="_blank" style="font-size:0.78rem;color:#3498DB;">View source ↗</a></div>'
    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SimulationCard
# ---------------------------------------------------------------------------

def SimulationCard(sim_data: dict[str, Any]) -> None:
    """Render a styled card for one simulation result.

    Parameters
    ----------
    sim_data:
        Dict from ``discover_simulation_results()`` or ``discover_simulation_bundles()``.
    """
    scenario: str = sim_data.get("scenario") or sim_data.get("label") or "Unnamed Scenario"
    description: str = sim_data.get("description") or sim_data.get("simulation_requirement", "")
    tick_count: int = sim_data.get("tick_count") or sim_data.get("agent_count", 0)
    alert_count: int = len(sim_data.get("alerts", []))
    completed_at: str = sim_data.get("completed_at") or sim_data.get("published_at", "")

    # Severity color based on alert count
    if alert_count >= 3:
        border_color = SEVERITY_COLORS["high"]
    elif alert_count >= 1:
        border_color = SEVERITY_COLORS["medium"]
    else:
        border_color = SEVERITY_COLORS["low"]

    ts_display = completed_at[:16].replace("T", " ") if completed_at else "—"
    scenario_display = scenario.replace("_", " ").replace("-", " ").title()

    html = (
        f'<div style="{_border_style(border_color)}">'
        f'<div style="font-weight:600;font-size:0.95rem;margin-bottom:6px;">🎯 {scenario_display}</div>'
        f'<div style="font-size:0.82rem;color:#aaa;margin-bottom:6px;">{description[:100]}{"…" if len(description) > 100 else ""}</div>'
        f'<div style="font-size:0.8rem;display:flex;gap:16px;">'
        f'<span>⏱ {tick_count} ticks</span>'
        f'<span>🔔 {alert_count} alerts</span>'
        f'<span>🕐 {ts_display}</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    # Expandable predictions/alerts
    alerts = sim_data.get("alerts", [])
    predictions = sim_data.get("predictions", [])
    if alerts or predictions:
        with st.expander("Alerts & Predictions", expanded=False):
            if alerts:
                st.markdown("**Alerts**")
                for alert in alerts[:5]:
                    st.markdown(f"- {alert}")
            if predictions:
                st.markdown("**Predictions**")
                for pred in predictions[:5]:
                    st.markdown(f"- {pred}")
