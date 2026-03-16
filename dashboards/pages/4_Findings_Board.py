"""Findings Board — Rolling discoveries across all agents."""

import streamlit as st

from dashboards.dashboard_data import discover_agent_names, load_all_findings
from dashboards.components.risk_badge import render_risk_badge

st.set_page_config(page_title="Findings Board", layout="wide")
st.header("Findings Board")

agent_names = discover_agent_names()
findings = load_all_findings(agent_names)

if not findings:
    st.info("No findings yet. Run agent workflows to generate discoveries.")
    if agent_names:
        st.caption(f"Runnable agents with no findings artifacts yet: {', '.join(agent_names)}")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Findings", len(findings))
    col2.metric("Agents With Findings", len({finding.get("_agent", "") for finding in findings}))
    col3.metric("Action Required", sum(1 for finding in findings if finding.get("action_required")))

    col_s1, col_s2, col_s3 = st.columns(3)
    severities = sorted({finding.get("severity", "info") for finding in findings})
    selected_severity = col_s1.selectbox("Severity Filter", ["All"] + severities)
    agents_list = sorted({finding.get("_agent", "") for finding in findings if finding.get("_agent")})
    selected_agent = col_s2.selectbox("Agent Filter", ["All"] + agents_list)
    finding_types = sorted({finding.get("finding_type", "") for finding in findings if finding.get("finding_type")})
    selected_type = col_s3.selectbox("Type Filter", ["All"] + finding_types)

    filtered = findings
    if selected_severity != "All":
        filtered = [finding for finding in filtered if finding.get("severity") == selected_severity]
    if selected_agent != "All":
        filtered = [finding for finding in filtered if finding.get("_agent") == selected_agent]
    if selected_type != "All":
        filtered = [finding for finding in filtered if finding.get("finding_type") == selected_type]

    st.write(f"Showing {len(filtered)} findings")

    if not filtered:
        st.info("No findings match the selected filters.")
    else:
        for finding in filtered[:100]:
            severity = finding.get("severity", "info")
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "info": "🔵"}.get(
                severity,
                "⚪",
            )
            
            # Use risk badge for asset or company
            entity = finding.get("company") or finding.get("asset") or "N/A"
            
            st.markdown("---")
            c1, c2 = st.columns([1, 15])
            with c1:
                render_risk_badge(entity)
            with c2:
                st.markdown(
                    f"{icon} **[{finding.get('finding_type', 'unknown')}]** "
                    f"{finding.get('asset', 'N/A')} ({finding.get('_agent', '')}) — "
                    f"{finding.get('summary', '')}"
                )
                st.caption(
                    f"Company: {finding.get('company', 'N/A')} | "
                    f"Source: {finding.get('source_url', 'N/A')} | "
                    f"Confidence: {finding.get('confidence', 'N/A')} | "
                    f"Action Required: {finding.get('action_required', False)}"
                )
