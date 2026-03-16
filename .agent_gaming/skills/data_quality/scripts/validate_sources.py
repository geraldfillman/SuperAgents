"""
Data Quality — Validate Sources (Gaming)

Thin wrapper around the shared validation module.
Previously 85 lines of standalone logic; now delegates to
super_agents.common.validate with gaming-specific data directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.common.validate import print_report, validate_sources
from super_agents.common.paths import DATA_DIR

GAMING_DATA_DIR = DATA_DIR / "processed"


def run(check_urls: bool = False) -> dict:
    """Run gaming source validation."""
    return validate_sources(
        data_dir=GAMING_DATA_DIR,
        check_urls=check_urls,
        check_fda_flag=False,  # not relevant for gaming
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate gaming data source integrity")
    parser.add_argument("--check-urls", action="store_true", help="Check URL validity (slower)")
    args = parser.parse_args()

    report = run(check_urls=args.check_urls)
    print_report(report)
