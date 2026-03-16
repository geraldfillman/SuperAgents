"""
Fetch and normalize the CISA Known Exploited Vulnerabilities catalog.
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
from super_agents.cybersecurity.cisa import (
    build_findings,
    fetch_kev_catalog,
    normalize_kev_catalog,
    select_recent_records,
)
from super_agents.cybersecurity.paths import DASHBOARDS_DIR, KEV_PROCESSED_DIR, KEV_RAW_DIR
from super_agents.cybersecurity.watchlist import load_asset_watchlist

AGENT_NAME = "cybersecurity"
WORKFLOW_NAME = "threat_landscape"
TASK_NAME = "fetch_kev_catalog"
KEV_LATEST_PATH = DASHBOARDS_DIR / "cybersecurity_kev_latest.json"
FINDINGS_LATEST_PATH = DASHBOARDS_DIR / "cybersecurity_findings_latest.json"


def _days_arg(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 365:
        raise argparse.ArgumentTypeError("--days must be between 1 and 365")
    return parsed


def _limit_arg(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 500:
        raise argparse.ArgumentTypeError("--limit must be between 1 and 500")
    return parsed


def _safe_message(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {exc}"


def _write_failure_status(
    *,
    run_id: str,
    started_at: datetime,
    blocker: str,
) -> None:
    write_current_status(
        agent_name=AGENT_NAME,
        run_id=run_id,
        workflow_name=WORKFLOW_NAME,
        task_name=TASK_NAME,
        status="failed",
        input_scope=["feed:kev"],
        active_source="CISA KEV",
        progress_completed=0,
        progress_total=3,
        current_focus="Fetch failed",
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
        inputs={},
        outputs={},
        blockers=[blocker],
        next_actions=["Retry the KEV fetch or replay the run with --input-file."],
    )


def run(*, days: int, limit: int, input_file: Path | None = None) -> int:
    started_at = datetime.now()
    run_id = started_at.strftime("%Y%m%d_%H%M%S")
    raw_path: Path | None = None

    write_current_status(
        agent_name=AGENT_NAME,
        run_id=run_id,
        workflow_name=WORKFLOW_NAME,
        task_name=TASK_NAME,
        status="running",
        input_scope=[f"days:{days}", "feed:kev"],
        active_source="CISA KEV",
        progress_completed=0,
        progress_total=3,
        current_focus="Loading watchlists",
        latest_message="Preparing cybersecurity watchlist context.",
    )

    try:
        asset_watchlist = load_asset_watchlist()

        if input_file:
            payload = read_json(input_file)
            source_label = f"file:{input_file.name}"
        else:
            payload = fetch_kev_catalog()
            raw_path = KEV_RAW_DIR / f"kev_catalog_raw_{run_id}.json"
            write_json(raw_path, payload)
            source_label = "CISA KEV"

        write_current_status(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="running",
            input_scope=[f"days:{days}", "feed:kev"],
            active_source=source_label,
            progress_completed=1,
            progress_total=3,
            current_focus="Normalizing KEV entries",
            latest_message="Transforming raw feed rows into dashboard records.",
        )

        records = normalize_kev_catalog(payload, assets=asset_watchlist)
        recent_records = select_recent_records(records, days=days)[:limit]
        findings = build_findings(recent_records, limit=min(limit, 25))

        processed_path = KEV_PROCESSED_DIR / f"kev_catalog_{run_id}.json"
        write_json(processed_path, recent_records)
        write_json(KEV_LATEST_PATH, recent_records)
        write_json(FINDINGS_LATEST_PATH, findings)

        watchlist_hits = sum(1 for record in recent_records if record.get("watchlist_match"))
        ransomware_hits = sum(
            1
            for record in recent_records
            if str(record.get("known_ransomware_campaign_use", "")).lower() == "known"
        )
        files_written = 3 + (1 if raw_path else 0)

        write_current_status(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="completed",
            input_scope=[f"days:{days}", "feed:kev"],
            active_source=source_label,
            progress_completed=3,
            progress_total=3,
            current_focus="Artifacts written",
            latest_message=f"Wrote {len(recent_records)} KEV records for the dashboard.",
        )

        write_run_summary(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="completed",
            started_at=started_at,
            completed_at=datetime.now(),
            inputs={"days": days, "limit": limit},
            outputs={
                "records_written": len(recent_records),
                "files_written": files_written,
                "watchlist_hits": watchlist_hits,
                "ransomware_hits": ransomware_hits,
            },
            findings=findings,
            next_actions=[
                "Run build_patch_calendar to refresh due-date views from the latest KEV artifact.",
            ],
        )

        print(f"Saved {len(recent_records)} KEV records to {processed_path}")
        print(f"Updated dashboard feed: {KEV_LATEST_PATH}")
        print(f"Updated findings feed: {FINDINGS_LATEST_PATH}")
        return 0
    except Exception as exc:
        blocker = _safe_message(exc)
        _write_failure_status(run_id=run_id, started_at=started_at, blocker=blocker)
        print(f"Failed to fetch KEV catalog: {blocker}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch the CISA KEV catalog")
    parser.add_argument("--days", type=_days_arg, default=30, help="Lookback window in days")
    parser.add_argument("--limit", type=_limit_arg, default=50, help="Maximum KEV records to keep")
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Replay the fetch from a local KEV JSON payload instead of hitting the live feed",
    )
    args = parser.parse_args()
    return run(days=args.days, limit=args.limit, input_file=args.input_file)


if __name__ == "__main__":
    raise SystemExit(main())
