"""Fetch FAA commercial space pages and match them to tracked companies."""

from __future__ import annotations

import argparse

from adt_agent.faa import (
    FAA_PAGE_CATALOG,
    build_faa_query_manifest,
    fetch_faa_pages,
    normalize_faa_matches,
    save_faa_pages,
    save_faa_query_manifest,
    save_faa_signals,
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
        return [CompanyRecord(company_name=args.company, ticker=args.ticker or "")]

    raise SystemExit("Provide --company, --ticker, or --watchlist.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch FAA licensing and stakeholder signals")
    parser.add_argument("--company", help="Company name")
    parser.add_argument("--ticker", help="Optional watchlist ticker")
    parser.add_argument("--watchlist", action="store_true", help="Run across the watchlist")
    parser.add_argument("--url", action="append", help="Optional FAA page URL override; can be repeated")
    parser.add_argument("--manifests-only", action="store_true", help="Save manifests without fetching pages")
    args = parser.parse_args()

    companies = _resolve_companies(args)
    systems = load_system_watchlist()
    selected_tickers = {company.ticker.upper() for company in companies}
    selected_systems = [system for system in systems if system.ticker.upper() in selected_tickers]
    urls = tuple(args.url) if args.url else FAA_PAGE_CATALOG

    manifest_paths = []
    for company in companies:
        company_systems = [system for system in selected_systems if system.ticker.upper() == company.ticker.upper()]
        manifest = build_faa_query_manifest(company, systems=company_systems, urls=urls)
        manifest_paths.append(save_faa_query_manifest(manifest, label=company.ticker or company.company_name))

    if args.manifests_only:
        print(f"Wrote {len(manifest_paths)} FAA query manifest(s)")
        for path in manifest_paths:
            print(path)
        return

    raw_pages: list[dict] = []
    failure_message = ""
    try:
        raw_pages = fetch_faa_pages(urls=urls)
    except Exception as exc:
        failure_message = str(exc)

    normalized_records = normalize_faa_matches(raw_pages, companies=companies, systems=selected_systems)
    label = args.ticker or ("watchlist" if args.watchlist else args.company or "query")
    raw_path = save_faa_pages(raw_pages, label=label)
    processed_path = save_faa_signals(normalized_records, label=label)

    print(f"Wrote {len(manifest_paths)} FAA query manifest(s)")
    for path in manifest_paths:
        print(path)
    print(f"Fetched {len(raw_pages)} FAA page(s)")
    print(raw_path)
    print(f"Matched {len(normalized_records)} FAA signal record(s)")
    print(processed_path)
    if failure_message:
        print(failure_message)


if __name__ == "__main__":
    main()
