"""Run a prepared MiroFish bundle against a local MiroFish checkout."""

from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.integrations.mirofish.runtime import launch_simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", required=True, help="Directory containing simulation_config.json.")
    parser.add_argument(
        "--runtime-path",
        help="Path to a local MiroFish checkout. Falls back to SUPER_AGENTS_MIROFISH_HOME and common local paths.",
    )
    parser.add_argument(
        "--platform",
        choices=["parallel", "twitter", "reddit"],
        default="parallel",
        help="Runner variant to execute.",
    )
    parser.add_argument("--max-rounds", type=int, help="Optional cap on executed rounds.")
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Exit after the simulation run instead of waiting for IPC commands.",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Launch the runtime in the background and write output to mirofish_runtime.log.",
    )
    parser.add_argument(
        "--openai-defaults",
        action="store_true",
        help="Force OpenAI-compatible base/model defaults for this run if they are unset.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = launch_simulation(
            args.bundle_dir,
            runtime_home=args.runtime_path,
            platform=args.platform,
            max_rounds=args.max_rounds,
            no_wait=args.no_wait,
            background=args.background,
            openai_defaults=args.openai_defaults,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["mode"] == "background":
        print(f"Started MiroFish runtime in background (pid={result['pid']})")
        print(f"Log file: {result['log_path']}")
    else:
        print(f"Runtime exited with code {result['returncode']}")
    return int(result.get("returncode", 0))


if __name__ == "__main__":
    raise SystemExit(main())
