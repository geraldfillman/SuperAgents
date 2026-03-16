"""
Calendar -- Build forward-looking calendar of CODs, PPA expirations, and permit deadlines.
"""

import json
import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.common.io_utils import write_json
from super_agents.common.run_summary import write_run_summary
from super_agents.common.status import write_current_status

AGENT_NAME = "renewable_energy"
WORKFLOW_NAME = "calendar"
TASK_NAME = "build_calendar"
PROCESSED_DIR = Path("data/processed/renewable_energy")
OUTPUT_DIR = Path("dashboards")


def build_calendar(
    days: int = 180,
    ticker: str | None = None,
    format: str = "json",
    output_path: str | None = None,
) -> list[dict]:
    """
    Build a rolling calendar by merging data from:
    - interconnection events (milestone dates)
    - PPA agreements (expiration dates, announcement dates)
    - project milestones (COD dates, construction start)
    - IRA credits (certification deadlines)

    Args:
        days: Number of days to look ahead
        ticker: Optional ticker filter
        format: Output format ("json" or "csv")
        output_path: Optional file path for output
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cutoff_date = datetime.now() + timedelta(days=days)
    today = datetime.now()

    events: list[dict] = []

    # 1. Interconnection milestones
    events.extend(_load_interconnection_events(today, cutoff_date, ticker))

    # 2. PPA-related dates
    events.extend(_load_ppa_events(today, cutoff_date, ticker))

    # 3. Project milestones (CODs, construction)
    events.extend(_load_project_milestones(today, cutoff_date, ticker))

    # 4. IRA credit deadlines
    events.extend(_load_credit_deadlines(today, cutoff_date, ticker))

    # Sort by date
    events.sort(key=lambda x: x.get("date", "9999-99-99"))

    # Output
    out = _resolve_output_path(days=days, format=format, output_path=output_path)
    if output_path or format == "csv":
        if format == "csv":
            _write_csv(events, out)
        else:
            write_json(out, events)
        print(f"Saved {len(events)} events to {out}")
    else:
        write_json(out, events)

    return events


def _resolve_output_path(days: int, format: str, output_path: str | None) -> Path:
    if output_path:
        return Path(output_path)
    suffix = "csv" if format == "csv" else "json"
    return OUTPUT_DIR / f"energy_calendar_{days}d.{suffix}"


def _build_findings(events: list[dict], limit: int = 5) -> list[dict]:
    findings: list[dict] = []
    for event in events[:limit]:
        label = event.get("project") or event.get("ticker") or "renewable energy event"
        findings.append(
            {
                "severity": "info",
                "asset": label,
                "finding_type": event.get("event_type", "calendar_event"),
                "summary": f"{event.get('event_type', 'event')} for {label} on {event.get('date', '')}",
                "source_url": event.get("source_url", ""),
                "confidence": event.get("source_confidence", ""),
            }
        )
    return findings


def _parse_date(value: str) -> date | None:
    """Parse supported date formats into a date object."""
    if not value:
        return None

    candidate = value.strip()
    for parser in (datetime.fromisoformat,):
        try:
            return parser(candidate).date()
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d", "%Y-%m", "%B %d, %Y", "%b %d, %Y"):
        try:
            parsed = datetime.strptime(candidate, fmt)
        except ValueError:
            continue
        if fmt == "%Y-%m":
            return parsed.date().replace(day=1)
        return parsed.date()

    return None


def _is_in_window(value: str, start: datetime, end: datetime) -> bool:
    """Return True when the date falls within the requested rolling window."""
    parsed = _parse_date(value)
    if parsed is None:
        return False
    return start.date() <= parsed <= end.date()


def _load_interconnection_events(
    start: datetime, end: datetime, ticker: str | None,
) -> list[dict]:
    """Load interconnection milestone events."""
    events_dir = PROCESSED_DIR / "interconnection"
    if not events_dir.exists():
        return []

    events = []
    for f in events_dir.glob("*.json"):
        records = json.loads(f.read_text())
        if not isinstance(records, list):
            records = [records]

        for record in records:
            event_date = record.get("milestone_date", "")
            if not event_date or not _is_in_window(event_date, start, end):
                continue
            if ticker and record.get("ticker", "").upper() != ticker.upper():
                continue

            events.append({
                "date": _parse_date(event_date).isoformat(),
                "ticker": record.get("ticker", ""),
                "project": record.get("project_name", ""),
                "event_type": "interconnection_milestone",
                "detail": record.get("status", ""),
                "iso_region": record.get("iso_region", ""),
                "source_url": record.get("source_url", ""),
                "source_confidence": record.get("source_confidence", ""),
            })

    return events


def _load_ppa_events(
    start: datetime, end: datetime, ticker: str | None,
) -> list[dict]:
    """Load PPA announcement and expiration dates."""
    ppa_dir = PROCESSED_DIR / "ppa"
    if not ppa_dir.exists():
        return []

    events = []
    for f in ppa_dir.glob("*.json"):
        records = json.loads(f.read_text())
        if not isinstance(records, list):
            records = [records]

        for record in records:
            announced = record.get("announced_date", "")
            if announced and _is_in_window(announced, start, end):
                if not ticker or record.get("ticker", "").upper() == ticker.upper():
                    events.append({
                        "date": _parse_date(announced).isoformat(),
                        "ticker": record.get("ticker", ""),
                        "project": record.get("project_name", ""),
                        "event_type": "ppa_announced",
                        "detail": f"Offtaker: {record.get('offtaker', 'N/A')}",
                        "source_url": record.get("source_url", ""),
                        "source_confidence": record.get("source_confidence", ""),
                    })

    return events


def _load_project_milestones(
    start: datetime, end: datetime, ticker: str | None,
) -> list[dict]:
    """Load project milestones (COD, construction start, etc.)."""
    milestones_dir = PROCESSED_DIR / "milestones"
    if not milestones_dir.exists():
        return []

    events = []
    for f in milestones_dir.glob("*.json"):
        records = json.loads(f.read_text())
        if not isinstance(records, list):
            records = [records]

        for record in records:
            milestone_date = (
                record.get("expected_cod")
                or record.get("milestone_date")
                or record.get("filing_date", "")
            )
            if not milestone_date or not _is_in_window(milestone_date, start, end):
                continue
            if ticker and record.get("ticker", "").upper() != ticker.upper():
                continue

            events.append({
                "date": _parse_date(milestone_date).isoformat(),
                "ticker": record.get("ticker", ""),
                "project": record.get("project_name", record.get("company_name", "")),
                "event_type": record.get("milestone_type", "project_milestone"),
                "detail": record.get("milestone_type", ""),
                "source_url": record.get("source_url", ""),
                "source_confidence": record.get("source_confidence", ""),
            })

    return events


def _load_credit_deadlines(
    start: datetime, end: datetime, ticker: str | None,
) -> list[dict]:
    """Load IRA credit certification deadlines."""
    credits_dir = PROCESSED_DIR / "ira_credits"
    if not credits_dir.exists():
        return []

    events = []
    for f in credits_dir.glob("*.json"):
        records = json.loads(f.read_text())
        if not isinstance(records, list):
            records = [records]

        for record in records:
            pub_date = record.get("publication_date", "")
            if not pub_date or not _is_in_window(pub_date, start, end):
                continue

            events.append({
                "date": _parse_date(pub_date).isoformat(),
                "ticker": "",
                "project": "",
                "event_type": "ira_credit_update",
                "detail": f"{record.get('credit_type', '')} - {record.get('title', '')[:60]}",
                "source_url": record.get("source_url", ""),
                "source_confidence": record.get("source_confidence", ""),
            })

    return events


def _write_csv(events: list[dict], path: Path) -> None:
    """Write events to CSV."""
    fieldnames = [
        "date", "ticker", "project", "event_type", "detail",
        "source_url", "source_confidence",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(events)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Build forward-looking energy project calendar"
    )
    parser.add_argument("--window-days", type=int, default=180, help="Days to look ahead")
    parser.add_argument("--ticker", type=str, help="Filter by ticker")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()

    started_at = datetime.now()
    run_id = started_at.strftime("%Y%m%d_%H%M%S")
    input_scope = [f"window:{args.window_days}d"]
    if args.ticker:
        input_scope.append(args.ticker.upper())

    write_current_status(
        agent_name=AGENT_NAME,
        run_id=run_id,
        workflow_name=WORKFLOW_NAME,
        task_name=TASK_NAME,
        status="running",
        input_scope=input_scope,
        active_source="data/processed/renewable_energy",
        progress_completed=0,
        progress_total=4,
        current_focus="Building renewable energy calendar",
        latest_message="Collecting renewable energy events from processed artifacts",
    )

    try:
        results = build_calendar(
            days=args.window_days,
            ticker=args.ticker,
            format=args.format,
            output_path=args.output,
        )
        output_file = _resolve_output_path(
            days=args.window_days,
            format=args.format,
            output_path=args.output,
        )

        write_current_status(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="completed",
            input_scope=input_scope,
            active_source="data/processed/renewable_energy",
            progress_completed=4,
            progress_total=4,
            current_focus="Renewable energy calendar ready",
            latest_message=f"Built {len(results)} calendar events",
        )
        write_run_summary(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="completed",
            started_at=started_at,
            inputs={
                "window_days": args.window_days,
                "ticker_filters": 1 if args.ticker else 0,
                "sources_checked": 4,
            },
            outputs={
                "records_written": len(results),
                "files_written": 1 if output_file.exists() else 0,
            },
            findings=_build_findings(results),
            next_actions=[
                "Review the renewable energy calendar and confirm which sectors still lack calendar coverage",
            ],
        )
        print(f"Built calendar with {len(results)} events over next {args.window_days} days")
    except Exception as exc:
        write_current_status(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="failed",
            input_scope=input_scope,
            active_source="data/processed/renewable_energy",
            progress_completed=0,
            progress_total=4,
            current_focus="Renewable energy calendar build failed",
            latest_message=str(exc),
            blocker=str(exc),
        )
        write_run_summary(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="failed",
            started_at=started_at,
            inputs={
                "window_days": args.window_days,
                "ticker_filters": 1 if args.ticker else 0,
                "sources_checked": 4,
            },
            outputs={"records_written": 0, "files_written": 0},
            blockers=[str(exc)],
            next_actions=[
                "Inspect processed renewable energy inputs and rerun the calendar builder",
            ],
        )
        raise


if __name__ == "__main__":
    main()
