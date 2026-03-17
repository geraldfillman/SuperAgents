"""Reusable Plotly chart components for the Super Agents dashboard."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------------------------
# Dark theme defaults
# ---------------------------------------------------------------------------

_DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(20,20,30,0.8)",
    font=dict(color="#E0E0E0", size=12),
    margin=dict(l=40, r=20, t=40, b=40),
)

_GRID_STYLE = dict(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.15)")

_STATUS_COLORS: dict[str, str] = {
    "completed": "#2ECC71",
    "passed": "#2ECC71",
    "pass": "#2ECC71",
    "running": "#3498DB",
    "failed": "#E74C3C",
    "fail": "#E74C3C",
    "idle": "#95A5A6",
}

_SEVERITY_COLORS: dict[str, str] = {
    "critical": "#E74C3C",
    "high": "#E67E22",
    "medium": "#F1C40F",
    "low": "#3498DB",
    "info": "#95A5A6",
}


def _apply_dark(fig: go.Figure) -> go.Figure:
    fig.update_layout(**_DARK_LAYOUT)
    return fig


# ---------------------------------------------------------------------------
# Chart functions
# ---------------------------------------------------------------------------

def sector_heatmap(data: list[dict[str, Any]]) -> go.Figure:
    """Signal density heatmap: sectors (y-axis) x date (x-axis).

    Parameters
    ----------
    data:
        List of dicts with keys: ``sector``, ``date`` (ISO string), optional ``count``.
    """
    if not data:
        fig = go.Figure()
        fig.update_layout(title="Sector Signal Density (no data)", **_DARK_LAYOUT)
        return fig

    sectors: list[str] = sorted({d.get("sector", "unknown") for d in data})
    dates: list[str] = sorted({d.get("date", "")[:10] for d in data if d.get("date")})

    # Build z matrix (sector x date)
    lookup: dict[tuple[str, str], int] = {}
    for d in data:
        key = (d.get("sector", "unknown"), (d.get("date", ""))[:10])
        lookup[key] = lookup.get(key, 0) + d.get("count", 1)

    z = [[lookup.get((s, dt), 0) for dt in dates] for s in sectors]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=dates,
            y=sectors,
            colorscale="YlOrRd",
            showscale=True,
            hoverongaps=False,
        )
    )
    fig.update_layout(
        title="Signal Density by Sector",
        xaxis=dict(title="Date", **_GRID_STYLE),
        yaxis=dict(title="Sector"),
        **_DARK_LAYOUT,
    )
    return fig


def run_timeline(runs: list[dict[str, Any]]) -> go.Figure:
    """Scatter/bar chart of agent runs over time, colored by status.

    Parameters
    ----------
    runs:
        List of run dicts with keys: ``started_at``, ``agent``, ``status``, ``skill``.
    """
    if not runs:
        fig = go.Figure()
        fig.update_layout(title="Run Timeline (no data)", **_DARK_LAYOUT)
        return fig

    traces: dict[str, dict[str, list[Any]]] = {}
    for run in runs:
        status = (run.get("status") or "idle").lower()
        color = _STATUS_COLORS.get(status, "#95A5A6")
        if status not in traces:
            traces[status] = {"x": [], "y": [], "text": [], "color": color}
        traces[status]["x"].append(run.get("started_at", ""))
        traces[status]["y"].append(run.get("agent", "unknown"))
        skill = run.get("skill", run.get("script", ""))
        traces[status]["text"].append(f"{run.get('agent', '')} / {skill}")

    fig = go.Figure()
    for status, td in traces.items():
        fig.add_trace(
            go.Scatter(
                x=td["x"],
                y=td["y"],
                mode="markers",
                name=status.title(),
                text=td["text"],
                hovertemplate="%{text}<br>%{x}<extra></extra>",
                marker=dict(color=td["color"], size=10, symbol="circle"),
            )
        )

    fig.update_layout(
        title="Run Timeline",
        xaxis=dict(title="Time", **_GRID_STYLE),
        yaxis=dict(title="Agent"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        **_DARK_LAYOUT,
    )
    return fig


def finding_treemap(findings: list[dict[str, Any]]) -> go.Figure:
    """Treemap of findings grouped by sector then severity.

    Parameters
    ----------
    findings:
        List of finding dicts with keys: ``sector`` / ``_agent``, ``severity``, ``title``.
    """
    if not findings:
        fig = go.Figure()
        fig.update_layout(title="Findings Treemap (no data)", **_DARK_LAYOUT)
        return fig

    ids: list[str] = ["All Findings"]
    labels: list[str] = ["All Findings"]
    parents: list[str] = [""]
    values: list[int] = [0]
    colors: list[str] = ["#2C3E50"]

    sector_counts: dict[str, int] = {}
    sector_severity: dict[str, dict[str, int]] = {}

    for f in findings:
        sector = f.get("sector") or f.get("_agent") or "unknown"
        severity = (f.get("severity") or "info").lower()
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        if sector not in sector_severity:
            sector_severity[sector] = {}
        sector_severity[sector][severity] = sector_severity[sector].get(severity, 0) + 1

    for sector, count in sorted(sector_counts.items()):
        ids.append(sector)
        labels.append(sector.replace("_", " ").title())
        parents.append("All Findings")
        values.append(count)
        colors.append("#3498DB")

        for severity, sev_count in sorted(sector_severity[sector].items()):
            node_id = f"{sector}/{severity}"
            ids.append(node_id)
            labels.append(severity.title())
            parents.append(sector)
            values.append(sev_count)
            colors.append(_SEVERITY_COLORS.get(severity, "#95A5A6"))

    fig = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            marker=dict(colors=colors),
            textinfo="label+value",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>",
        )
    )
    fig.update_layout(title="Findings by Sector & Severity", **_DARK_LAYOUT)
    return fig


def signal_sankey(signals: list[dict[str, Any]]) -> go.Figure:
    """Sankey diagram: source → topic → sector.

    Parameters
    ----------
    signals:
        List of signal dicts with keys: ``source``, ``topic``, ``sector``.
    """
    if not signals:
        fig = go.Figure()
        fig.update_layout(title="Signal Flow (no data)", **_DARK_LAYOUT)
        return fig

    sources: list[str] = sorted({s.get("source", "unknown") for s in signals})
    topics: list[str] = sorted({s.get("topic", "unknown") for s in signals})
    sectors: list[str] = sorted({s.get("sector", "unknown") for s in signals})

    all_nodes = sources + topics + sectors
    node_idx: dict[str, int] = {n: i for i, n in enumerate(all_nodes)}

    link_src: list[int] = []
    link_tgt: list[int] = []
    link_val: list[int] = []
    link_map: dict[tuple[int, int], int] = {}

    for sig in signals:
        src = sig.get("source", "unknown")
        topic = sig.get("topic", "unknown")
        sector = sig.get("sector", "unknown")
        # source → topic
        key_st = (node_idx[src], node_idx[topic])
        link_map[key_st] = link_map.get(key_st, 0) + 1
        # topic → sector
        key_ts = (node_idx[topic], node_idx[sector])
        link_map[key_ts] = link_map.get(key_ts, 0) + 1

    for (s, t), v in link_map.items():
        link_src.append(s)
        link_tgt.append(t)
        link_val.append(v)

    node_colors = (
        ["#3498DB"] * len(sources)
        + ["#9B59B6"] * len(topics)
        + ["#2ECC71"] * len(sectors)
    )

    fig = go.Figure(
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="rgba(255,255,255,0.2)", width=0.5),
                label=all_nodes,
                color=node_colors,
            ),
            link=dict(
                source=link_src,
                target=link_tgt,
                value=link_val,
                color="rgba(100,100,200,0.3)",
            ),
        )
    )
    fig.update_layout(title="Signal Flow: Source → Topic → Sector", **_DARK_LAYOUT)
    return fig


def cost_burn_chart(metrics: list[dict[str, Any]]) -> go.Figure:
    """Cumulative line chart of LLM token costs over time.

    Parameters
    ----------
    metrics:
        List of dicts with keys: ``timestamp``, ``cost_usd``, optional ``model``.
    """
    if not metrics:
        fig = go.Figure()
        fig.update_layout(title="LLM Cost Burn (no data)", **_DARK_LAYOUT)
        return fig

    sorted_metrics = sorted(metrics, key=lambda m: m.get("timestamp", ""))
    by_model: dict[str, dict[str, list[Any]]] = {}

    for m in sorted_metrics:
        model = m.get("model", "unknown")
        if model not in by_model:
            by_model[model] = {"x": [], "y": [], "cumulative": 0.0}
        by_model[model]["cumulative"] += float(m.get("cost_usd", 0))
        by_model[model]["x"].append(m.get("timestamp", ""))
        by_model[model]["y"].append(by_model[model]["cumulative"])

    fig = go.Figure()
    for model, td in by_model.items():
        fig.add_trace(
            go.Scatter(
                x=td["x"],
                y=td["y"],
                mode="lines+markers",
                name=model,
                fill="tozeroy",
                hovertemplate="%{x}<br>$%{y:.4f}<extra>" + model + "</extra>",
            )
        )

    fig.update_layout(
        title="Cumulative LLM Cost ($)",
        xaxis=dict(title="Time", **_GRID_STYLE),
        yaxis=dict(title="USD", **_GRID_STYLE),
        **_DARK_LAYOUT,
    )
    return fig


def risk_radar(risk_data: dict[str, float]) -> go.Figure:
    """Spider/radar chart of risk categories.

    Parameters
    ----------
    risk_data:
        Dict mapping category name to a 0–100 risk score.
    """
    if not risk_data:
        fig = go.Figure()
        fig.update_layout(title="Risk Radar (no data)", **_DARK_LAYOUT)
        return fig

    categories = list(risk_data.keys())
    values = [float(risk_data[c]) for c in categories]
    # Close the polygon
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure(
        go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill="toself",
            fillcolor="rgba(231,76,60,0.2)",
            line=dict(color="#E74C3C", width=2),
            name="Risk Score",
        )
    )
    fig.update_layout(
        title="Risk Radar",
        polar=dict(
            bgcolor="rgba(20,20,30,0.8)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor="rgba(255,255,255,0.1)",
                color="#E0E0E0",
            ),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.1)", color="#E0E0E0"),
        ),
        **_DARK_LAYOUT,
    )
    return fig


def activity_sparkline(data: list[float | int], *, color: str = "#3498DB") -> go.Figure:
    """Tiny inline sparkline for agent cards.

    Parameters
    ----------
    data:
        Ordered sequence of activity values (e.g. daily run counts).
    color:
        Line color hex string.
    """
    fig = go.Figure(
        go.Scatter(
            y=data,
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=f"{color}33",
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig
