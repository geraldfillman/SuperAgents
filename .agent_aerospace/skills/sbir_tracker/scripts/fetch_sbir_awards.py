"""Fetch SBIR awards for tracked companies or a manual company query."""

from __future__ import annotations

import argparse

from super_agents.aerospace.sbir import (
    build_sbir_query_manifest,
    fetch_sbir_award_pages,
    match_sbir_awards_to_companies,
    normalize_sbir_award_match,
    save_normalized_sbir_awards,
    save_raw_sbir_pages,
    save_sbir_query_manifest,
)
from super_agents.aerospace.watchlist import CompanyRecord, find_company, load_company_watchlist


def _resolve_companies(args: argparse.Namespace) -> list[CompanyRecord]:
    if args.watchlist:
        return load_company_watchlist()

    if args.ticker or args.company:
        company = find_company(ticker=args.ticker, company_name=args.company)
        if company is not None:
            return [company]

    if args.company:
        return [CompanyRecord(company_name=args.company, ticker=args.ticker or "")]

    raise SystemExit("Provide --company, --ticker, or --watchlist.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch SBIR awards for tracked companies")
    parser.add_argument("--company", help="Company name")
    parser.add_argument("--ticker", help="Optional watchlist ticker")
    parser.add_argument("--agency", help="Optional agency filter")
    parser.add_argument("--year", type=int, help="Optional award year filter")
    parser.add_argument("--watchlist", action="store_true", help="Run across the watchlist")
    parser.add_argument("--rows", type=int, default=100, help="Rows per page")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum pages to fetch per company query")
    args = parser.parse_args()

    companies = _resolve_companies(args)
    raw_pages: list[dict] = []
    matches: list[dict] = []
    failures: list[str] = []
    manifest_paths = []

    for company in companies:
        manifest = build_sbir_query_manifest(
            company,
            agency=args.agency,
            year=args.year,
            rows=args.rows,
        )
        manifest_paths.append(save_sbir_query_manifest(manifest, label=company.ticker or company.company_name))
        try:
            company_pages = fetch_sbir_award_pages(
                firm=company.company_name,
                agency=args.agency,
                year=args.year,
                rows=args.rows,
                max_pages=args.max_pages,
            )
        except Exception as exc:
            failures.append(f"{company.ticker or company.company_name}: {exc}")
            continue
        raw_pages.extend(company_pages)
        matches.extend(match_sbir_awards_to_companies(company_pages, [company]))

    normalized_records = [normalize_sbir_award_match(match) for match in matches]
    label = args.ticker or ("watchlist" if args.watchlist else args.company or "query")
    raw_path = save_raw_sbir_pages(raw_pages, label=label)
    processed_path = save_normalized_sbir_awards(normalized_records, label=label)

    print(f"Wrote {len(manifest_paths)} SBIR query manifest(s)")
    for path in manifest_paths:
        print(path)
    print(f"Fetched {len(raw_pages)} SBIR page(s)")
    print(raw_path)
    print(f"Matched {len(normalized_records)} SBIR award record(s)")
    print(processed_path)
    if failures:
        print(f"Failures: {len(failures)}")
        for failure in failures:
            print(failure)


if __name__ == "__main__":
    main()
