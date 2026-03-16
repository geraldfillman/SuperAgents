"""Build a rolling defense program calendar from processed records."""

from __future__ import annotations

import argparse
from pathlib import Path

from adt_agent.calendar import build_program_calendar, write_calendar_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a rolling program calendar")
    parser.add_argument("--days", type=int, default=90, help="Forward-looking window")
    parser.add_argument("--processed-root", type=Path, help="Override processed data root")
    parser.add_argument("--dashboards-dir", type=Path, help="Override dashboards output directory")
    args = parser.parse_args()

    payload = build_program_calendar(days=args.days, processed_root=args.processed_root)
    written_paths = write_calendar_snapshot(payload, args.days, dashboards_dir=args.dashboards_dir)
    print(f"Saved {len(payload['upcoming'])} upcoming and {len(payload['overdue'])} overdue record(s)")
    for path in written_paths:
        print(path)


if __name__ == "__main__":
    main()
