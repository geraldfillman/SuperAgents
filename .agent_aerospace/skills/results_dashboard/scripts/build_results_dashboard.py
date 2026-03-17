"""Build a static HTML dashboard from the agent's result artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from super_agents.aerospace.dashboard import build_results_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static agent results dashboard")
    parser.add_argument("--ranking", type=Path, help="Optional ranking JSON path")
    parser.add_argument("--scorecards", type=Path, help="Optional scorecards JSON path")
    parser.add_argument("--calendar", type=Path, help="Optional program calendar JSON path")
    parser.add_argument("--overdue", type=Path, help="Optional overdue calendar JSON path")
    parser.add_argument("--output", type=Path, help="Optional HTML output path")
    args = parser.parse_args()

    out_path = build_results_dashboard(
        ranking_path=args.ranking,
        scorecards_path=args.scorecards,
        calendar_path=args.calendar,
        overdue_path=args.overdue,
        output_path=args.output,
    )
    print(out_path)


if __name__ == "__main__":
    main()
