"""Send a close-env IPC command to a running MiroFish simulation bundle."""

from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.integrations.mirofish.status import send_close_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", required=True, help="Directory containing the running bundle.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Requested timeout metadata to include with the close command.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = send_close_command(args.bundle_dir, timeout=args.timeout)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote close command: {result['command_id']}")
        print(f"Command file: {result['command_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
