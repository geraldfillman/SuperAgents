"""Publish a completed MiroFish bundle into Zep and register it with the local MiroFish app."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.integrations.mirofish.zep import publish_bundle_to_zep


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", required=True, help="Directory containing simulation_config.json and action logs.")
    parser.add_argument("--runtime-path", help="Path to a local MiroFish checkout.")
    parser.add_argument("--graph-name", help="Optional override for the created Zep graph name.")
    parser.add_argument("--project-name", help="Optional override for the imported local MiroFish project name.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing local imported project/simulation IDs.")
    parser.add_argument("--poll-seconds", type=float, default=2.0, help="Wait time between graph-data polling attempts.")
    parser.add_argument("--poll-attempts", type=int, default=10, help="Maximum graph-data polling attempts.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = publish_bundle_to_zep(
            args.bundle_dir,
            runtime_home=args.runtime_path,
            graph_name=args.graph_name,
            project_name=args.project_name,
            force=args.force,
            poll_seconds=args.poll_seconds,
            poll_attempts=args.poll_attempts,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Graph ID: {result['graph_id']}")
        print(f"Project URL: {result['process_url']}")
        print(f"Simulation URL: {result['simulation_url']}")
        print(f"Saved result: {result['result_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
