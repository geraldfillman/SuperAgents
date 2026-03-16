"""
Data Quality — Validate Sources (Rare Earth)

Thin wrapper around the shared validation module.
Previously 160 lines of standalone logic; now delegates to
super_agents.common.validate with rare-earth-specific data directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.common.validate import print_report, validate_sources
from super_agents.common.paths import DATA_DIR

RARE_EARTH_DATA_DIR = DATA_DIR / "processed" / "rare_earth"


def run(check_urls: bool = False) -> dict:
    """Run rare earth source validation."""
    return validate_sources(
        data_dir=RARE_EARTH_DATA_DIR,
        check_urls=check_urls,
        check_fda_flag=False,  # not relevant for rare earth
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate rare earth data source integrity")
    parser.add_argument("--check-urls", action="store_true", help="Check URL validity (slower)")
    args = parser.parse_args()

    report = run(check_urls=args.check_urls)
    print_report(report)
