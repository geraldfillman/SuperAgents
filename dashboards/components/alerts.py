"""Alert bar component — persistent banner for critical/high findings."""

from __future__ import annotations

from typing import Any

import streamlit as st

from dashboards.components.theme import SEVERITY_COLORS, get_severity_icon

# Session-state key for dismissed alerts
_DISMISSED_KEY = "_dismissed_alert_ids"


def _get_dismissed() -> set[str]:
    if _DISMISSED_KEY not in st.session_state:
        st.session_state[_DISMISSED_KEY] = set()
    return st.session_state[_DISMISSED_KEY]


def _finding_id(finding: dict[str, Any]) -> str:
    """Derive a stable ID for a finding (for dismiss tracking)."""
    return str(
        finding.get("id")
        or finding.get("finding_id")
        or f"{finding.get('_agent','')}/{finding.get('finding_time','')}/{finding.get('title','')}"
    )


def _highest_severity(findings: list[dict[str, Any]]) -> str:
    order = ["critical", "high", "medium", "low", "info"]
    severities = {(f.get("severity") or "info").lower() for f in findings}
    for sev in order:
        if sev in severities:
            return sev
    return "info"


def render_alert_bar(findings: list[dict[str, Any]]) -> None:
    """Render a persistent alert banner at the top of the page.

    Only shows critical and high severity findings that have not been
    dismissed during the current session.

    Parameters
    ----------
    findings:
        Full list of findings (will be filtered to critical/high internally).
    """
    # Filter to critical/high only
    actionable = [
        f for f in findings
        if (f.get("severity") or "info").lower() in ("critical", "high")
    ]
    if not actionable:
        return

    dismissed = _get_dismissed()
    visible = [f for f in actionable if _finding_id(f) not in dismissed]

    if not visible:
        return

    highest = _highest_severity(visible)
    bar_color = SEVERITY_COLORS.get(highest, SEVERITY_COLORS["high"])
    icon = get_severity_icon(highest)
    count = len(visible)

    with st.container():
        col_msg, col_btn = st.columns([9, 1])

        with col_msg:
            label = "CRITICAL ALERT" if highest == "critical" else "HIGH ALERT"
            titles = [f.get("title", "Untitled") for f in visible[:3]]
            preview = " · ".join(t[:60] for t in titles)
            if count > 3:
                preview += f" (+{count - 3} more)"

            st.markdown(
                f'<div style="background:{bar_color}22;border-left:4px solid {bar_color};'
                f'padding:10px 14px;border-radius:4px;margin-bottom:8px;">'
                f'<strong>{icon} {label}</strong> ({count}) — {preview}'
                f'</div>',
                unsafe_allow_html=True,
            )

        with col_btn:
            if st.button("✕ Dismiss", key="_alert_bar_dismiss", use_container_width=True):
                for f in visible:
                    dismissed.add(_finding_id(f))
                st.session_state[_DISMISSED_KEY] = dismissed
                st.rerun()


def render_alert_history(findings: list[dict[str, Any]]) -> None:
    """Render a collapsible log of all critical/high findings.

    Parameters
    ----------
    findings:
        Full findings list.
    """
    actionable = [
        f for f in findings
        if (f.get("severity") or "info").lower() in ("critical", "high")
    ]
    if not actionable:
        st.info("No critical or high severity findings.")
        return

    with st.expander(f"Alert History ({len(actionable)} items)", expanded=False):
        for f in actionable:
            severity = (f.get("severity") or "high").lower()
            icon = get_severity_icon(severity)
            color = SEVERITY_COLORS.get(severity, "#E67E22")
            title = f.get("title", "Untitled")
            ts = (f.get("finding_time", ""))[:16].replace("T", " ")
            agent = f.get("_agent") or f.get("sector") or ""

            st.markdown(
                f'<div style="border-left:3px solid {color};padding:6px 12px;margin:4px 0;">'
                f'{icon} <strong>{title}</strong>'
                f'<span style="color:#888;font-size:0.8rem;float:right">{agent} · {ts}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
