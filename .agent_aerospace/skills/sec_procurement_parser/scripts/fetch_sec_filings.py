"""Fetch recent SEC filings and cache their raw text for procurement parsing."""

from __future__ import annotations

import argparse

from super_agents.aerospace.sec import fetch_and_cache_sec_filings


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch recent SEC filings and cache raw text")
    parser.add_argument("--cik", help="Explicit CIK")
    parser.add_argument("--ticker", help="Ticker resolved via the SEC company_tickers mapping")
    parser.add_argument("--limit", type=int, default=5, help="Maximum filings to fetch")
    parser.add_argument("--types", nargs="+", default=["8-K", "10-Q", "10-K"], help="Filing types to fetch")
    parser.add_argument("--refresh-ticker-map", action="store_true", help="Refresh the cached SEC ticker map first")
    args = parser.parse_args()

    if not args.cik and not args.ticker:
        raise SystemExit("Provide --cik or --ticker.")

    result = fetch_and_cache_sec_filings(
        cik=args.cik,
        ticker=args.ticker,
        filing_types=tuple(args.types),
        limit=args.limit,
        force_refresh_ticker_map=args.refresh_ticker_map,
    )
    print(f"Cached {len(result['filings'])} filing text file(s)")
    print(result["submissions_path"])
    print(result["manifest_path"])
    for filing in result["filings"]:
        print(filing["text_path"])


if __name__ == "__main__":
    main()
