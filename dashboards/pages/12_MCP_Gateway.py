"""MCP Gateway — server health, registered tools, and live tool calls."""

from __future__ import annotations

import streamlit as st

from dashboards.dashboard_data import (
    AGENT_SECTOR_MAP,
    MCP_SERVER_URL,
    get_agent_sector,
    load_gateway_health,
    load_gateway_tools,
)
from dashboards.components.theme import setup_page, apply_custom_css
from dashboards.components.empty_state import render_empty_state

setup_page("MCP Gateway", "🔌")
apply_custom_css()

st.header("MCP Gateway")
st.caption(
    f"Single multi-agent MCP server — all 13 sector agents exposed as namespaced tools. "
    f"Server: `{MCP_SERVER_URL}`"
)

# ---------------------------------------------------------------------------
# Health row
# ---------------------------------------------------------------------------

health = load_gateway_health()
is_online = health.get("status") == "ok"

status_label = "🟢 Online" if is_online else "🔴 Offline"
col1, col2, col3, col4 = st.columns(4)
col1.metric("Server", status_label)
col2.metric("Agents", health.get("agents", "—"))
col3.metric("Skills", health.get("skills", "—"))
col4.metric("Tools", health.get("tools", "—"))

if not is_online:
    render_empty_state(
        f"MCP server is unreachable at `{MCP_SERVER_URL}`.\n\n"
        "Start the server with `docker compose up` or `python -m super_agents.mcp.server`.",
        "docker compose up mcp-server",
    )
    st.stop()

st.divider()

# ---------------------------------------------------------------------------
# Tool browser
# ---------------------------------------------------------------------------

st.subheader("Tool Browser")

tools = load_gateway_tools()

if not tools:
    st.warning("Server is online but returned no tools.")
    st.stop()

# Build sector breakdown from tool names
sector_counts: dict[str, int] = {}
for tool in tools:
    sector = tool["name"].split("__")[0] if "__" in tool["name"] else "unknown"
    sector_counts[sector] = sector_counts.get(sector, 0) + 1

# Sector filter
all_sectors = sorted(sector_counts.keys())
selected_sector = st.selectbox(
    "Filter by sector",
    ["All"] + all_sectors,
    format_func=lambda s: s if s == "All" else f"{get_agent_sector(s).get('icon', '')} {s} ({sector_counts.get(s, 0)} tools)",
)

filtered_tools = tools
if selected_sector != "All":
    prefix = f"{selected_sector}__"
    filtered_tools = [t for t in tools if t["name"].startswith(prefix)]

# Tool search
search = st.text_input("Search tools", placeholder="e.g. fetch_approvals")
if search:
    filtered_tools = [t for t in filtered_tools if search.lower() in t["name"].lower() or search.lower() in t.get("description", "").lower()]

st.caption(f"{len(filtered_tools)} of {len(tools)} tools shown")

# Tool table
if filtered_tools:
    import pandas as pd
    rows = []
    for tool in filtered_tools:
        parts = tool["name"].split("__")
        rows.append({
            "Agent": parts[0] if len(parts) > 0 else "",
            "Skill": parts[1] if len(parts) > 1 else "",
            "Script": parts[2] if len(parts) > 2 else "",
            "Tool Name": tool["name"],
            "Description": tool.get("description", ""),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df[["Agent", "Skill", "Script", "Description"]], use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Sector breakdown chart
# ---------------------------------------------------------------------------

st.subheader("Tools by Sector")
if sector_counts:
    import pandas as pd
    chart_data = pd.DataFrame(
        [{"Sector": s, "Tools": c} for s, c in sorted(sector_counts.items(), key=lambda x: -x[1])]
    )
    st.bar_chart(chart_data.set_index("Sector")["Tools"])

st.divider()

# ---------------------------------------------------------------------------
# Live tool call
# ---------------------------------------------------------------------------

st.subheader("Call a Tool")
st.caption("Runs the script on the MCP server and streams output back.")

tool_names = [t["name"] for t in tools]
selected_tool = st.selectbox("Select tool", tool_names)
args_input = st.text_input("Arguments (space-separated)", placeholder="--days 30 --limit 10")

if st.button("Run Tool", type="primary"):
    args = args_input.split() if args_input.strip() else []
    with st.spinner(f"Running `{selected_tool}`..."):
        from super_agents.orchestrator.gateway_client import get_gateway_client
        result = get_gateway_client().call_tool(selected_tool, args=args)

    if "error" in result:
        st.error(f"Error: {result['error']}")
    else:
        exit_code = result.get("exit_code", 0)
        if exit_code == 0:
            st.success(f"Exit 0")
        else:
            st.warning(f"Exit {exit_code}")
        st.code(result.get("output", "(no output)"), language=None)
        if result.get("stderr"):
            with st.expander("stderr"):
                st.code(result["stderr"], language=None)
