"""Static HTML dashboard builder for agent results."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import html
from pathlib import Path

from .io_utils import read_json
from .paths import DASHBOARDS_DIR, ensure_directory, project_path

DEFAULT_RANKING_PATH = DASHBOARDS_DIR / "watchlist_ranking_watchlist.json"
DEFAULT_SCORECARDS_PATH = DASHBOARDS_DIR / "company_scorecards_watchlist.json"
DEFAULT_CALENDAR_PATH = DASHBOARDS_DIR / "program_calendar_90d.json"
DEFAULT_OVERDUE_PATH = DASHBOARDS_DIR / "program_calendar_overdue.json"
DEFAULT_OUTPUT_PATH = DASHBOARDS_DIR / "agent_results_dashboard.html"
DEFAULT_DASHBOARD_INDEX_PATH = DASHBOARDS_DIR / "index.html"
DEFAULT_SITE_INDEX_PATH = project_path("index.html")

COMPONENT_LABELS = (
    ("awards", "Awards"),
    ("procurement", "Procurement"),
    ("execution", "Execution"),
    ("budget", "Budget"),
    ("financial", "Financial"),
    ("insider", "Insider"),
)


def _read_optional_json(path: Path, fallback):
    if not path.exists():
        return fallback
    payload = read_json(path)
    if isinstance(fallback, dict) and isinstance(payload, dict):
        return payload
    if isinstance(fallback, list) and isinstance(payload, list):
        return payload
    return fallback


def _format_currency(value: float | int | None) -> str:
    amount = float(value or 0.0)
    absolute = abs(amount)
    if absolute >= 1_000_000_000:
        return f"${amount / 1_000_000_000:,.2f}B"
    if absolute >= 1_000_000:
        return f"${amount / 1_000_000:,.1f}M"
    return f"${amount:,.0f}"


def _format_months(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    months = float(value)
    if months >= 100:
        return f"{months:,.0f} months"
    return f"{months:,.1f} months".replace(".0 ", " ")


def _format_score(value: float | int | None) -> str:
    return f"{float(value or 0.0):.2f}".rstrip("0").rstrip(".")


def _format_datetime(value: str) -> str:
    if not value:
        return "n/a"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%b %d, %Y %H:%M")


def _priority_class(priority: str) -> str:
    return {
        "high": "priority-high",
        "medium": "priority-medium",
        "low": "priority-low",
    }.get(str(priority or "").lower(), "priority-neutral")


def _priority_badge(priority: str) -> str:
    label = str(priority or "unknown").title()
    return f'<span class="priority-pill {_priority_class(priority)}">{html.escape(label)}</span>'


def _metric_card(label: str, value: str, detail: str, tone: str) -> str:
    return (
        f'<article class="metric-card {tone}">'
        f'<p class="metric-label">{html.escape(label)}</p>'
        f'<p class="metric-value">{html.escape(value)}</p>'
        f'<p class="metric-detail">{html.escape(detail)}</p>'
        "</article>"
    )


def _tag_list(items: list[str], kind: str) -> str:
    if not items:
        return '<p class="empty-inline">None surfaced</p>'
    tags = "".join(f'<li class="{kind}">{html.escape(item)}</li>' for item in items)
    return f'<ul class="tag-list">{tags}</ul>'


def _component_meter(label: str, value: float | int | None) -> str:
    score = max(0.0, min(100.0, float(value or 0.0)))
    return (
        '<div class="component-meter">'
        f'<div class="component-head"><span>{html.escape(label)}</span><span>{score:.0f}</span></div>'
        f'<div class="component-track"><span class="component-fill" style="width:{score:.1f}%"></span></div>'
        "</div>"
    )


def _spotlight_cards(rankings: list[dict], scorecards_by_ticker: dict[str, dict]) -> str:
    if not rankings:
        return '<div class="empty-panel">No ranked companies available yet.</div>'

    cards: list[str] = []
    for record in rankings[:4]:
        scorecard = scorecards_by_ticker.get(str(record.get("ticker", "")).upper(), {})
        systems = [item.get("system_name", "") for item in scorecard.get("systems", []) if item.get("system_name")]
        component_markup = "".join(
            _component_meter(label, record.get("score_components", {}).get(key))
            for key, label in COMPONENT_LABELS
        )
        cards.append(
            '<article class="spotlight-card">'
            '<div class="spotlight-top">'
            f'<div><p class="eyebrow small">Rank {int(record.get("rank", 0) or 0)}</p><h3>{html.escape(record.get("company_name", ""))}</h3></div>'
            f'{_priority_badge(str(record.get("priority", "")))}'
            "</div>"
            f'<p class="spotlight-score">Composite {_format_score(record.get("composite_score"))}</p>'
            f'<p class="spotlight-systems">{html.escape(", ".join(systems[:3]) or "No system mapping yet")}</p>'
            '<div class="pill-row">'
            f'<span>{html.escape(record.get("ticker", ""))}</span>'
            f'<span>Awards {_format_currency(record.get("contract_award_value_usd"))}</span>'
            f'<span>Budget {_format_currency(record.get("explicit_budget_exposure_usd"))}</span>'
            f'<span>Runway {_format_months(record.get("est_runway_months"))}</span>'
            "</div>"
            f'<div class="component-grid">{component_markup}</div>'
            '<div class="spotlight-foot">'
            f'<div><p class="mini-label">Reasons</p>{_tag_list(record.get("reasons", []), "reason-tag")}</div>'
            f'<div><p class="mini-label">Risks</p>{_tag_list(record.get("risks", []), "risk-tag")}</div>'
            "</div>"
            "</article>"
        )
    return "".join(cards)


def _ranking_rows(rankings: list[dict]) -> str:
    rows: list[str] = []
    for record in rankings:
        reasons = " | ".join(str(item) for item in record.get("reasons", []))
        risks = " | ".join(str(item) for item in record.get("risks", []))
        search_blob = " ".join(
            [str(record.get("ticker", "")), str(record.get("company_name", "")), reasons, risks]
        ).lower()
        rows.append(
            "<tr "
            f'data-priority="{html.escape(str(record.get("priority", "")).lower())}" '
            f'data-has-risk="{"1" if record.get("risks") else "0"}" '
            f'data-search="{html.escape(search_blob)}">'
            f'<td class="strong">{int(record.get("rank", 0) or 0)}</td>'
            f'<td><div class="company-cell"><strong>{html.escape(record.get("ticker", ""))}</strong><span>{html.escape(record.get("company_name", ""))}</span></div></td>'
            f"<td>{_priority_badge(str(record.get('priority', '')))}</td>"
            f'<td class="strong">{_format_score(record.get("composite_score"))}</td>'
            f'<td>{_format_currency(record.get("contract_award_value_usd"))}</td>'
            f'<td>{_format_currency(record.get("explicit_budget_exposure_usd"))}</td>'
            f'<td>{_format_months(record.get("est_runway_months"))}</td>'
            f'<td><div class="company-cell"><span>{int(record.get("high_priority_signal_count", 0) or 0)} high-priority</span><span>{int(record.get("budget_support_signal_count", 0) or 0)} budget supports</span></div></td>'
            f'<td><div class="reason-cell"><span>{html.escape(reasons or "None surfaced")}</span></div></td>'
            f'<td class="risk-text">{html.escape(risks or "Clear")}</td>'
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="10" class="empty-row">No ranking data available.</td></tr>'
    return "".join(rows)


def _calendar_cards(entries: list[dict], empty_text: str) -> str:
    if not entries:
        return f'<div class="empty-panel">{html.escape(empty_text)}</div>'
    cards = []
    for entry in entries[:8]:
        cards.append(
            '<article class="calendar-card">'
            f'<p class="eyebrow small">{html.escape(str(entry.get("date", "")))}</p>'
            f'<h4>{html.escape(str(entry.get("headline", "")))}</h4>'
            f'<p class="calendar-meta">{html.escape(str(entry.get("ticker", "")))} | {html.escape(str(entry.get("system_name", "")))} | {html.escape(str(entry.get("entry_type", "")))}</p>'
            f'<p class="calendar-meta">{html.escape(str(entry.get("status", "")))}</p>'
            "</article>"
        )
    return "".join(cards)


def _risk_summary(rankings: list[dict]) -> str:
    counts = Counter()
    for record in rankings:
        for risk in record.get("risks", []):
            counts[str(risk)] += 1
    if not counts:
        return '<div class="empty-panel">No surfaced risk labels yet.</div>'
    items = "".join(
        '<li class="summary-row">'
        f'<span>{html.escape(risk)}</span><strong>{count}</strong>'
        "</li>"
        for risk, count in counts.most_common(6)
    )
    return f'<ul class="summary-list">{items}</ul>'


def _method_notes(notes: list[str]) -> str:
    if not notes:
        return '<div class="empty-panel">No methodology notes provided.</div>'
    items = "".join(f"<li>{html.escape(note)}</li>" for note in notes)
    return f'<ul class="method-list">{items}</ul>'


def build_results_dashboard_html(
    *,
    ranking_bundle: dict | None = None,
    scorecard_bundle: dict | None = None,
    upcoming_entries: list[dict] | None = None,
    overdue_entries: list[dict] | None = None,
) -> str:
    """Build a self-contained HTML dashboard from current agent outputs."""
    ranking = ranking_bundle or {}
    scorecards = scorecard_bundle or {}
    upcoming = upcoming_entries or []
    overdue = overdue_entries or []

    rankings = list(ranking.get("rankings", []))
    company_scorecards = list(scorecards.get("company_scorecards", []))
    scorecards_by_ticker = {
        str(record.get("ticker", "")).upper(): record
        for record in company_scorecards
        if record.get("ticker")
    }

    ranking_summary = ranking.get("summary", {})
    scorecard_summary = scorecards.get("summary", {})
    notes = list(ranking.get("scoring_model", {}).get("notes", []))

    candidate_only_count = sum(
        1
        for record in rankings
        if float(record.get("candidate_budget_exposure_usd", 0.0) or 0.0) > 0
        and float(record.get("explicit_budget_exposure_usd", 0.0) or 0.0) <= 0
    )
    companies_with_risks = sum(1 for record in rankings if record.get("risks"))

    metrics = "".join(
        [
            _metric_card(
                "Top ranked",
                f"{ranking_summary.get('top_ticker', 'n/a')} | {_format_score(ranking_summary.get('top_score'))}",
                f"{int(ranking_summary.get('ranked_companies', 0) or 0)} names scored",
                "tone-alert",
            ),
            _metric_card(
                "Award coverage",
                _format_currency(scorecard_summary.get("total_contract_award_value_usd", 0.0)),
                "Total tracked contract award value",
                "tone-cool",
            ),
            _metric_card(
                "Budget mapped",
                _format_currency(scorecard_summary.get("explicit_budget_exposure_usd", 0.0)),
                f"{int(ranking_summary.get('companies_with_explicit_budget', 0) or 0)} names with explicit links",
                "tone-warm",
            ),
            _metric_card(
                "Financial coverage",
                str(int(ranking_summary.get("companies_with_financials", 0) or 0)),
                f"{candidate_only_count} names still rely on candidate-only budget links",
                "tone-cool",
            ),
            _metric_card(
                "Catalysts",
                str(len(upcoming)),
                f"{len(overdue)} overdue milestone(s) or test event(s)",
                "tone-warm",
            ),
            _metric_card(
                "Risk labels",
                str(companies_with_risks),
                "Companies with surfaced dashboard risks",
                "tone-alert",
            ),
        ]
    )

    generated_at = _format_datetime(str(ranking.get("generated_at", "") or scorecards.get("generated_at", "")))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ADT Agent Results Dashboard</title>
  <style>
    :root {{ --bg:#06111b; --panel:rgba(9,24,37,.88); --panel-2:rgba(14,33,49,.95); --line:rgba(145,176,196,.18); --text:#e7edf2; --muted:#8da1af; --accent:#72d4c9; --accent-2:#f1b46a; --alert:#ff8d6c; --shadow:0 18px 48px rgba(0,0,0,.28); }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Trebuchet MS","Gill Sans",sans-serif; color:var(--text); background:radial-gradient(circle at top left,rgba(114,212,201,.14),transparent 28%), radial-gradient(circle at top right,rgba(241,180,106,.16),transparent 24%), linear-gradient(180deg,#081723 0%,#06111b 56%,#03080d 100%); }}
    h1,h2,h3,h4 {{ margin:0; font-family:"Palatino Linotype","Book Antiqua",serif; }}
    .shell {{ width:min(1380px,calc(100% - 32px)); margin:0 auto; padding:28px 0 40px; }}
    .hero,.layout,.metric-grid,.spotlight-grid,.calendar-grid,.spotlight-foot,.component-grid {{ display:grid; gap:20px; }}
    .hero {{ grid-template-columns:1.8fr 1fr; margin-bottom:20px; }}
    .layout {{ grid-template-columns:1.35fr .85fr; }}
    .metric-grid {{ grid-template-columns:repeat(6,minmax(0,1fr)); margin-bottom:20px; gap:14px; }}
    .spotlight-grid,.calendar-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }}
    .spotlight-foot,.component-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
    .panel,.metric-card,.spotlight-card,.calendar-card {{ border:1px solid var(--line); background:var(--panel); border-radius:22px; box-shadow:var(--shadow); }}
    .hero-panel,.side-panel,.section-panel {{ border:1px solid var(--line); background:var(--panel); border-radius:22px; box-shadow:var(--shadow); padding:24px; }}
    .hero-panel {{ position:relative; overflow:hidden; }}
    .hero-panel::after {{ content:""; position:absolute; inset:auto -60px -60px auto; width:220px; height:220px; background:radial-gradient(circle,rgba(114,212,201,.2),transparent 70%); }}
    .side-panel {{ background:var(--panel-2); }}
    .eyebrow {{ margin:0 0 10px; color:var(--accent); letter-spacing:.16em; text-transform:uppercase; font-size:12px; }}
    .eyebrow.small {{ margin-bottom:8px; font-size:11px; }}
    h1 {{ font-size:clamp(2.2rem,4vw,3.8rem); line-height:.95; max-width:10ch; }}
    .hero-copy,.section-note,.metric-detail,.calendar-meta,.spotlight-systems,.company-cell span,.risk-text,.reason-cell span,.empty-inline,.empty-panel,.empty-row,.method-list li,.summary-row span {{ color:var(--muted); }}
    .hero-copy {{ max-width:62ch; line-height:1.6; margin:14px 0 18px; }}
    .hero-meta,.pill-row,.filter-bar,.spotlight-top,.section-head {{ display:flex; flex-wrap:wrap; gap:12px; }}
    .hero-meta span,.pill-row span,.priority-pill,.filter-chip {{ border-radius:999px; }}
    .hero-meta span,.pill-row span {{ padding:8px 12px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.06); font-size:13px; }}
    .metric-card {{ padding:18px; min-height:150px; }}
    .tone-alert {{ background:linear-gradient(180deg,rgba(255,141,108,.14),rgba(9,24,37,.9)); }}
    .tone-cool {{ background:linear-gradient(180deg,rgba(114,212,201,.1),rgba(9,24,37,.9)); }}
    .tone-warm {{ background:linear-gradient(180deg,rgba(241,180,106,.1),rgba(9,24,37,.9)); }}
    .metric-label,.mini-label,.component-head {{ text-transform:uppercase; letter-spacing:.1em; font-size:11px; }}
    .metric-label,.mini-label,.component-head,.section-note {{ color:var(--muted); }}
    .metric-value,.spotlight-score {{ margin:0 0 10px; font-size:1.7rem; font-weight:700; }}
    .section-panel {{ margin-bottom:20px; }}
    .section-head {{ justify-content:space-between; align-items:end; margin-bottom:18px; }}
    .section-title {{ font-size:1.5rem; }}
    .spotlight-card,.calendar-card {{ padding:18px; }}
    .component-head {{ display:flex; justify-content:space-between; margin-bottom:6px; }}
    .component-track {{ width:100%; height:8px; border-radius:999px; background:rgba(255,255,255,.08); overflow:hidden; }}
    .component-fill {{ display:block; height:100%; background:linear-gradient(90deg,var(--accent),var(--accent-2)); }}
    .tag-list,.summary-list,.method-list {{ list-style:none; padding:0; margin:0; display:grid; gap:8px; }}
    .tag-list {{ display:flex; flex-wrap:wrap; }}
    .reason-tag,.risk-tag {{ padding:7px 10px; border-radius:999px; font-size:12px; }}
    .reason-tag {{ background:rgba(114,212,201,.12); color:#d6f2ef; }}
    .risk-tag {{ background:rgba(255,141,108,.12); color:#ffd6cb; }}
    .summary-row,.method-list li {{ display:flex; justify-content:space-between; gap:16px; padding:12px 14px; border-radius:16px; background:rgba(255,255,255,.03); line-height:1.5; }}
    .method-list li {{ display:block; }}
    .filter-bar {{ margin-bottom:16px; align-items:center; }}
    .filter-bar input {{ flex:1 1 240px; min-width:0; border-radius:14px; border:1px solid var(--line); background:rgba(255,255,255,.04); color:var(--text); padding:12px 14px; font:inherit; }}
    .filter-chip {{ border:1px solid var(--line); background:rgba(255,255,255,.03); color:var(--text); padding:10px 12px; cursor:pointer; font:inherit; }}
    .filter-chip.active {{ background:rgba(114,212,201,.14); border-color:rgba(114,212,201,.35); }}
    .table-wrap {{ overflow:auto; border-radius:18px; border:1px solid var(--line); }}
    table {{ width:100%; border-collapse:collapse; min-width:1080px; }}
    thead {{ background:rgba(255,255,255,.03); }}
    th,td {{ padding:14px 12px; border-bottom:1px solid rgba(255,255,255,.06); text-align:left; vertical-align:top; font-size:14px; }}
    th {{ color:var(--muted); text-transform:uppercase; letter-spacing:.08em; font-size:11px; position:sticky; top:0; }}
    tbody tr:hover {{ background:rgba(255,255,255,.03); }}
    .company-cell {{ display:grid; gap:4px; }}
    .strong {{ font-weight:700; }}
    .priority-pill {{ display:inline-flex; align-items:center; padding:7px 10px; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
    .priority-high {{ background:rgba(255,141,108,.14); color:#ffd6cb; }}
    .priority-medium {{ background:rgba(241,180,106,.14); color:#ffe2ba; }}
    .priority-low {{ background:rgba(114,212,201,.12); color:#d7f5f1; }}
    .priority-neutral {{ background:rgba(255,255,255,.08); color:#dde6ed; }}
    @media (max-width:1180px) {{ .hero,.layout {{ grid-template-columns:1fr; }} .metric-grid {{ grid-template-columns:repeat(3,minmax(0,1fr)); }} }}
    @media (max-width:820px) {{ .shell {{ width:min(100% - 24px,1000px); padding-top:18px; }} .metric-grid,.spotlight-grid,.calendar-grid,.spotlight-foot,.component-grid {{ grid-template-columns:1fr; }} .section-head {{ align-items:start; flex-direction:column; }} }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-panel">
        <p class="eyebrow">Aerospace Defense Tech Agent</p>
        <h1>Agent Results Dashboard</h1>
        <p class="hero-copy">Single-page analyst view across ranking, budget exposure, financial durability, and near-term catalysts. This page is built directly from the agent's JSON outputs so the dashboard stays aligned with the current pipeline.</p>
        <div class="hero-meta">
          <span>Updated {html.escape(generated_at)}</span>
          <span>{int(ranking_summary.get("ranked_companies", 0) or 0)} ranked names</span>
          <span>{int(scorecard_summary.get("companies_with_budget_matches", 0) or 0)} names with budget matches</span>
        </div>
      </div>
      <aside class="side-panel">
        <p class="eyebrow">Method</p>
        <h2 class="section-title">Scoring notes</h2>
        {_method_notes(notes)}
      </aside>
    </section>
    <section class="metric-grid">{metrics}</section>
    <div class="layout">
      <main>
        <section class="section-panel">
          <div class="section-head">
            <div><p class="eyebrow">Rank board</p><h2 class="section-title">Priority spotlight</h2></div>
            <p class="section-note">Top names with component-level scoring and surfaced risks.</p>
          </div>
          <div class="spotlight-grid">{_spotlight_cards(rankings, scorecards_by_ticker)}</div>
        </section>
        <section class="section-panel">
          <div class="section-head">
            <div><p class="eyebrow">Watchlist</p><h2 class="section-title">Ranking table</h2></div>
            <p class="section-note">Searchable output across awards, budgets, execution, financials, and insider activity.</p>
          </div>
          <div class="filter-bar">
            <input id="ranking-search" type="search" placeholder="Search ticker, company, reason, or risk">
            <button class="filter-chip active" data-filter="all" type="button">All</button>
            <button class="filter-chip" data-filter="high" type="button">High priority</button>
            <button class="filter-chip" data-filter="medium" type="button">Medium</button>
            <button class="filter-chip" data-filter="low" type="button">Low</button>
            <button class="filter-chip" data-filter="risk" type="button">At risk</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Rank</th><th>Company</th><th>Priority</th><th>Score</th><th>Awards</th><th>Explicit budget</th><th>Runway</th><th>Signals</th><th>Reasons</th><th>Risks</th></tr>
              </thead>
              <tbody id="ranking-body">{_ranking_rows(rankings)}</tbody>
            </table>
          </div>
        </section>
      </main>
      <aside>
        <section class="section-panel">
          <div class="section-head">
            <div><p class="eyebrow">Catalysts</p><h2 class="section-title">Program calendar</h2></div>
            <p class="section-note">Near-term milestones and overdue events pulled into one panel.</p>
          </div>
          <div class="calendar-grid">
            <div><p class="mini-label">Upcoming</p>{_calendar_cards(upcoming, "No upcoming events in the current 90-day window.")}</div>
            <div><p class="mini-label">Overdue</p>{_calendar_cards(overdue, "No overdue events surfaced.")}</div>
          </div>
        </section>
        <section class="section-panel">
          <div class="section-head">
            <div><p class="eyebrow">Data quality</p><h2 class="section-title">Risk concentration</h2></div>
          </div>
          {_risk_summary(rankings)}
        </section>
      </aside>
    </div>
  </div>
  <script>
    const searchInput = document.getElementById("ranking-search");
    const filterButtons = Array.from(document.querySelectorAll(".filter-chip"));
    const rankingRows = Array.from(document.querySelectorAll("#ranking-body tr[data-search]"));
    let activeFilter = "all";
    function applyFilters() {{
      const query = (searchInput.value || "").trim().toLowerCase();
      rankingRows.forEach((row) => {{
        const matchesQuery = !query || row.dataset.search.includes(query);
        const matchesFilter = activeFilter === "all" || (activeFilter === "risk" ? row.dataset.hasRisk === "1" : row.dataset.priority === activeFilter);
        row.style.display = matchesQuery && matchesFilter ? "" : "none";
      }});
    }}
    filterButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        filterButtons.forEach((candidate) => candidate.classList.remove("active"));
        button.classList.add("active");
        activeFilter = button.dataset.filter || "all";
        applyFilters();
      }});
    }});
    searchInput.addEventListener("input", applyFilters);
  </script>
</body>
</html>
"""


def save_results_dashboard(html_document: str, output_path: Path | None = None) -> Path:
    """Write the rendered HTML dashboard to disk."""
    destination = output_path or DEFAULT_OUTPUT_PATH
    ensure_directory(destination.parent)
    destination.write_text(html_document, encoding="utf-8")
    if destination.resolve() == DEFAULT_OUTPUT_PATH.resolve():
        DEFAULT_DASHBOARD_INDEX_PATH.write_text(html_document, encoding="utf-8")
        DEFAULT_SITE_INDEX_PATH.write_text(html_document, encoding="utf-8")
    return destination


def build_results_dashboard(
    *,
    ranking_path: Path | None = None,
    scorecards_path: Path | None = None,
    calendar_path: Path | None = None,
    overdue_path: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """Build and save the HTML results dashboard from current dashboard JSON outputs."""
    html_document = build_results_dashboard_html(
        ranking_bundle=_read_optional_json(ranking_path or DEFAULT_RANKING_PATH, {}),
        scorecard_bundle=_read_optional_json(scorecards_path or DEFAULT_SCORECARDS_PATH, {}),
        upcoming_entries=_read_optional_json(calendar_path or DEFAULT_CALENDAR_PATH, []),
        overdue_entries=_read_optional_json(overdue_path or DEFAULT_OVERDUE_PATH, []),
    )
    return save_results_dashboard(html_document, output_path=output_path)
