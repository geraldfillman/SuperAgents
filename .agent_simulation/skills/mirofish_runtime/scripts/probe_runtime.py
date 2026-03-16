"""Validate that a local MiroFish checkout is available for Super_Agents runtime use."""

from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.integrations.mirofish.runtime import MIROFISH_HOME_ENV, check_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-path",
        help=f"Path to a local MiroFish checkout. Falls back to {MIROFISH_HOME_ENV}.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = check_runtime(args.runtime_path)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Runtime home: {result['runtime_home']}")
        print(f"Python: {result['python_executable']} ({result['python_version']})")
        print(f"Dependencies ready: {'yes' if result['ready'] else 'no'}")
        print(f"Config ready: {'yes' if result['config_ready'] else 'no'}")
        print(f"Runnable: {'yes' if result['runnable'] else 'no'}")
        if result["active_env_file"]:
            print(f"Active env file: {result['active_env_file']}")
        if result["example_env_file"] and not result["active_env_file"]:
            print(f"Example env file: {result['example_env_file']}")
        if result["effective_base_url"]:
            print(f"Base URL: {result['effective_base_url']}")
        if result["effective_model"]:
            print(f"Model: {result['effective_model']}")
        print(f"Boost config: {'enabled' if result['boost_enabled'] else 'disabled'}")
        if result["missing_packages"]:
            print(f"Missing packages: {', '.join(result['missing_packages'])}")
        for warning in result["config_warnings"]:
            print(f"Warning: {warning}")
        for error in result["config_errors"]:
            print(f"Error: {error}")
    return 0 if result["runnable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
