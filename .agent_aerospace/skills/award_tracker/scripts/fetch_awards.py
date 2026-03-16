"""Create saved award-query manifests or fetch live award matches from USAspending."""

from __future__ import annotations

import argparse
from pathlib import Path

from adt_agent.awards import build_manual_award_query, build_watchlist_manifests, save_award_query_manifest
from adt_agent.usaspending import (
    fetch_award_search_pages,
    match_awards_to_companies,
    normalize_award_match,
    save_normalized_awards,
    save_raw_award_pages,
)
from adt_agent.watchlist import CompanyRecord, find_company, load_company_watchlist


def _resolve_companies(args: argparse.Namespace) -> list[CompanyRecord]:
    if args.watchlist:
        return load_company_watchlist()

    if args.ticker or args.company:
        company = find_company(ticker=args.ticker, company_name=args.company)
        if company is not None:
            return [company]

    if args.company:
        return [
            CompanyRecord(
                company_name=args.company,
                ticker=args.ticker or "",
                cage_code=args.cage_code or "",
                ueid=args.ueid or "",
            )
        ]

    raise SystemExit("Provide --company, --ticker, or --watchlist.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create award-query manifests")
    parser.add_argument("--company", help="Company name to search for")
    parser.add_argument("--ticker", help="Optional ticker lookup for the tracked watchlist")
    parser.add_argument("--cage-code", help="Optional CAGE code for manual queries")
    parser.add_argument("--ueid", help="Optional UEID for manual queries")
    parser.add_argument("--agency", help="Optional agency filter")
    parser.add_argument("--days", type=int, default=30, help="Lookback window")
    parser.add_argument("--watchlist", action="store_true", help="Generate manifests from data/seeds/company_watchlist.csv")
    parser.add_argument("--output-dir", type=Path, help="Override output directory")
    parser.add_argument("--live", action="store_true", help="Fetch and normalize live award matches from USAspending")
    parser.add_argument("--page-size", type=int, default=50, help="Live fetch page size")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum pages per award-type group for live fetch")
    parser.add_argument("--contracts-only", action="store_true", help="Skip IDV queries during live fetch")
    args = parser.parse_args()

    if args.live:
        companies = _resolve_companies(args)
        raw_pages = fetch_award_search_pages(
            days=args.days,
            agency=args.agency,
            page_size=args.page_size,
            max_pages=args.max_pages,
            include_idvs=not args.contracts_only,
        )
        raw_path = save_raw_award_pages(raw_pages, agency=args.agency, label="live_search")
        matches = match_awards_to_companies(raw_pages, companies)
        normalized_records = [normalize_award_match(match) for match in matches]
        processed_path = save_normalized_awards(normalized_records, agency=args.agency, label="live_fetch")

        print(f"Fetched {len(raw_pages)} raw USAspending page(s)")
        print(raw_path)
        print(f"Matched {len(normalized_records)} award record(s) across {len(companies)} tracked company row(s)")
        print(processed_path)
        return

    if args.watchlist or args.ticker:
        written_paths = build_watchlist_manifests(
            ticker=args.ticker,
            company_name=args.company,
            agency=args.agency,
            days=args.days,
            output_dir=args.output_dir,
        )
        if not written_paths:
            raise SystemExit("No matching watchlist company was found.")

        print(f"Wrote {len(written_paths)} award-query manifest(s)")
        for path in written_paths:
            print(path)
        return

    if not args.company:
        raise SystemExit("Provide --company for a manual query or use --watchlist.")

    manifest = build_manual_award_query(
        args.company,
        ticker=args.ticker or "",
        cage_code=args.cage_code or "",
        ueid=args.ueid or "",
        agency=args.agency,
        days=args.days,
    )
    out_path = save_award_query_manifest(manifest, output_dir=args.output_dir)
    print(f"Saved award query manifest to {out_path}")


if __name__ == "__main__":
    main()
