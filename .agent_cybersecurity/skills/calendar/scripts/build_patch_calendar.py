"""
Build a rolling patch calendar from the latest cybersecurity KEV artifact.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.common.io_utils import read_json, write_json
from super_agents.common.run_summary import write_run_summary
from super_agents.common.status import write_current_status
from super_agents.cybersecurity.calendar import build_patch_calendar
from super_agents.cybersecurity.paths import CYBERSECURITY_CALENDAR_DIR, DASHBOARDS_DIR, KEV_PROCESSED_DIR

AGENT_NAME = "cybersecurity"
WORKFLOW_NAME = "calendar"
TASK_NAME = "build_patch_calendar"
PATCH_CALENDAR_LATEST_PATH = DASHBOARDS_DIR / "cybersecurity_patch_calendar.json"
KEV_LATEST_PATH = DASHBOARDS_DIR / "cybersecurity_kev_latest.json"


def _window_arg(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 365:
        raise argparse.ArgumentTypeError("--window-days must be between 1 and 365")
    return parsed


def _limit_arg(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 1000:
        raise argparse.ArgumentTypeError("--limit must be between 1 and 1000")
    return parsed


def _safe_message(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {exc}"


def _load_latest_records(input_file: Path | None = None) -> list[dict]:
    if input_file:
        payload = read_json(input_file)
        if not isinstance(payload, list):
            raise ValueError("Input file must contain a list of KEV records.")
        return [item for item in payload if isinstance(item, dict)]

    if KEV_LATEST_PATH.exists():
        payload = read_json(KEV_LATEST_PATH)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

    candidates = sorted(KEV_PROCESSED_DIR.glob("kev_catalog_*.json"), reverse=True)
    if not candidates:
        raise FileNotFoundError(
            "No KEV artifact found. Run fetch_kev_catalog first or provide --input-file."
        )
    payload = read_json(candidates[0])
    if not isinstance(payload, list):
        raise ValueError("Latest processed KEV artifact is not a list.")
    return [item for item in payload if isinstance(item, dict)]


def run(*, window_days: int, limit: int, input_file: Path | None = None) -> int:
    started_at = datetime.now()
    run_id = started_at.strftime("%Y%m%d_%H%M%S")

    write_current_status(
        agent_name=AGENT_NAME,
        run_id=run_id,
        workflow_name=WORKFLOW_NAME,
        task_name=TASK_NAME,
        status="running",
        input_scope=[f"window_days:{window_days}"],
        active_source="cybersecurity_kev_latest.json",
        progress_completed=0,
        progress_total=2,
        current_focus="Loading KEV artifact",
        latest_message="Reading the latest KEV records for due-date extraction.",
    )

    try:
        records = _load_latest_records(input_file)
        write_current_status(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="running",
            input_scope=[f"window_days:{window_days}"],
            active_source="cybersecurity_kev_latest.json",
            progress_completed=1,
            progress_total=2,
            current_focus="Building patch calendar",
            latest_message=f"Loaded {len(records)} KEV records.",
        )

        events = build_patch_calendar(records, window_days=window_days)[:limit]
        processed_path = CYBERSECURITY_CALENDAR_DIR / f"patch_calendar_{run_id}.json"
        write_json(processed_path, events)
        write_json(PATCH_CALENDAR_LATEST_PATH, events)

        findings = []
        for event in events[:10]:
            findings.append(
                {
                    "severity": event.get("severity", "medium"),
                    "asset": event.get("asset", event.get("cve_id", "")),
                    "finding_type": "patch_due",
                    "summary": (
                        f"{event.get('cve_id', 'KEV item')} due on {event.get('date', '')} "
                        f"for {event.get('asset', 'tracked asset')}"
                    ),
                    "source_url": event.get("source_url", ""),
                    "confidence": event.get("source_confidence", "primary"),
                    "finding_time": event.get("date", ""),
                }
            )

        write_current_status(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="completed",
            input_scope=[f"window_days:{window_days}"],
            active_source="cybersecurity_kev_latest.json",
            progress_completed=2,
            progress_total=2,
            current_focus="Calendar ready",
            latest_message=f"Wrote {len(events)} patch calendar events.",
        )

        write_run_summary(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="completed",
            started_at=started_at,
            completed_at=datetime.now(),
            inputs={"window_days": window_days, "limit": limit},
            outputs={
                "records_written": len(events),
                "files_written": 2,
                "records_examined": len(records),
            },
            findings=findings,
            next_actions=["Review overdue or near-term due dates on the cybersecurity dashboard."],
        )

        print(f"Saved {len(events)} patch calendar events to {processed_path}")
        print(f"Updated dashboard feed: {PATCH_CALENDAR_LATEST_PATH}")
        return 0
    except Exception as exc:
        blocker = _safe_message(exc)
        write_current_status(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="failed",
            input_scope=[f"window_days:{window_days}"],
            active_source="cybersecurity_kev_latest.json",
            progress_completed=0,
            progress_total=2,
            current_focus="Calendar build failed",
            latest_message=blocker,
            blocker=blocker,
        )
        write_run_summary(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="failed",
            started_at=started_at,
            completed_at=datetime.now(),
            inputs={"window_days": window_days, "limit": limit},
            outputs={},
            blockers=[blocker],
            next_actions=["Refresh the KEV artifact before rebuilding the patch calendar."],
        )
        print(f"Failed to build patch calendar: {blocker}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a patch calendar from KEV records")
    parser.add_argument(
        "--window-days",
        type=_window_arg,
        default=30,
        help="How many days ahead to include in the calendar",
    )
    parser.add_argument("--limit", type=_limit_arg, default=100, help="Maximum events to keep")
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Replay the calendar build from a local KEV artifact instead of the dashboard feed",
    )
    args = parser.parse_args()
    return run(window_days=args.window_days, limit=args.limit, input_file=args.input_file)


if __name__ == "__main__":
    raise SystemExit(main())
