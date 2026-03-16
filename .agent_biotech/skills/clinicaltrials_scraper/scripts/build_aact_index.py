"""
Build the local AACT fallback index from a downloaded AACT flatfile snapshot.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from aact_fallback import build_aact_index, find_latest_aact_archive


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local AACT SQLite index")
    parser.add_argument("--archive", type=Path, help="Path to a downloaded AACT zip archive")
    args = parser.parse_args()

    archive_path = args.archive or find_latest_aact_archive()
    if archive_path is None:
        raise SystemExit("No AACT archive found in data/raw/clinicaltrials/aact/.")

    build_aact_index(archive_path)


if __name__ == "__main__":
    main()
