"""Build a portable MiroFish simulation bundle from a JSON or YAML spec."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.integrations.mirofish import create_bundle_from_spec, load_bundle_spec, read_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, help="Path to a JSON or YAML bundle spec.")
    parser.add_argument(
        "--output-dir",
        help="Directory where the bundle should be written. Defaults to data/processed/mirofish_simulations/<simulation_id>.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into an existing non-empty bundle directory.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        spec = load_bundle_spec(Path(args.spec))
        bundle_dir = create_bundle_from_spec(spec, args.output_dir, overwrite=args.overwrite)
        summary = read_bundle(bundle_dir)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Bundle created: {bundle_dir}")
        print(f"Simulation ID: {summary['simulation_id']}")
        print(f"Agents: {summary['agent_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
