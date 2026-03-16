"""Create SAM query manifests or fetch live SAM opportunity signals."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the shared library is importable when run as a script
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from super_agents.common.env import require_env

from adt_agent.sam import (
    build_sam_query_manifest,
    fetch_sam_opportunity_pages,
    normalize_pipeline_results,
    save_normalized_pipeline_signals,
    save_raw_sam_pages,
    save_sam_query_manifest,
)
from adt_agent.watchlist import CompanyRecord, find_company, load_company_watchlist, load_system_watchlist


def _resolve_companies(args: argparse.Namespace) -> list[CompanyRecord]:
    if args.watchlist:
        return load_company_watchlist()

    if args.ticker or args.company:
        company = find_company(ticker=args.ticker, company_name=args.company)
        if company is not None:
            return [company]

    if args.company:
        return [CompanyRecord(company_name=args.company, ticker=args.ticker or "", ueid=args.ueid or "")]

    raise SystemExit("Provide --company, --ticker, or --watchlist.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SAM pipeline manifests or fetch live signals")
    parser.add_argument("--company", help="Company name")
    parser.add_argument("--ticker", help="Optional watchlist ticker")
    parser.add_argument("--ueid", help="Optional UEID for manual rows")
    parser.add_argument("--agency", help="Optional agency filter note")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days (1–365)")
    parser.add_argument("--watchlist", action="store_true", help="Run across the watchlist")
    parser.add_argument("--live", action="store_true", help="Fetch live SAM opportunities")
    parser.add_argument("--page-size", type=int, default=100, help="Rows per page during live fetch (1–1000)")
    parser.add_argument("--max-pages", type=int, default=3, help="Maximum pages to fetch per query (1–50)")
    args = parser.parse_args()

    # --- Input bounds validation ---
    if not (1 <= args.days <= 365):
        parser.error("--days must be between 1 and 365")
    if not (1 <= args.page_size <= 1000):
        parser.error("--page-size must be between 1 and 1000")
    if not (1 <= args.max_pages <= 50):
        parser.error("--max-pages must be between 1 and 50")

    companies = _resolve_companies(args)
    systems = load_system_watchlist()

    manifests: list[dict] = []
    manifest_paths = []
    for company in companies:
        company_systems = [system for system in systems if system.ticker.upper() == company.ticker.upper()]
        manifest = build_sam_query_manifest(
            company,
            systems=company_systems,
            days=args.days,
            agency=args.agency,
        )
        manifests.append(manifest)
        manifest_paths.append(save_sam_query_manifest(manifest, label=company.ticker or company.company_name))

    if not args.live:
        print(f"Wrote {len(manifest_paths)} SAM query manifest(s)")
        for path in manifest_paths:
            print(path)
        return

    api_key = require_env("SAM_API_KEY")

    raw_pages: list[dict] = []
    normalized_records: list[dict] = []
    for company, manifest in zip(companies, manifests):
        for query in manifest["queries"]:
            query_row = {
                "keyword": query["keyword"],
                "system_name": query.get("system_name", ""),
                "posted_from": manifest["posted_from"],
                "posted_to": manifest["posted_to"],
            }
            company_pages = fetch_sam_opportunity_pages(
                query_row,
                api_key=api_key,
                page_size=args.page_size,
                max_pages=args.max_pages,
            )
            raw_pages.extend(company_pages)
            normalized_records.extend(normalize_pipeline_results(company_pages, company))

    label = args.ticker or ("watchlist" if args.watchlist else args.company or "query")
    raw_path = save_raw_sam_pages(raw_pages, label=label)
    processed_path = save_normalized_pipeline_signals(normalized_records, label=label)

    print(f"Wrote {len(manifest_paths)} SAM query manifest(s)")
    for path in manifest_paths:
        print(path)
    print(f"Fetched {len(raw_pages)} SAM page(s)")
    print(raw_path)
    print(f"Normalized {len(normalized_records)} pipeline signal record(s)")
    print(processed_path)


if __name__ == "__main__":
    main()
