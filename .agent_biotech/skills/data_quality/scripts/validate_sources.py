"""
Data Quality — Validate Sources (Biotech)

Thin wrapper around the shared validation module.
Previously this was 145 lines of standalone logic; now it delegates
to super_agents.common.validate with biotech-specific settings.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.common.validate import print_report, validate_sources
from super_agents.common.paths import DATA_DIR

BIOTECH_DATA_DIR = DATA_DIR / "processed"


def run(check_urls: bool = False) -> dict:
    """Run biotech source validation with FDA-specific checks enabled."""
    return validate_sources(
        data_dir=BIOTECH_DATA_DIR,
        check_urls=check_urls,
        check_fda_flag=True,  # biotech-specific: require official_fda_source_present
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate biotech data source integrity")
    parser.add_argument("--check-urls", action="store_true", help="Check URL validity (slower)")
    args = parser.parse_args()

    report = run(check_urls=args.check_urls)
    print_report(report)
