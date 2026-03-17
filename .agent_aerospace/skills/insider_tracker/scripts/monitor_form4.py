"""Fetch and normalize recent SEC Form 4 filings."""

from __future__ import annotations

import argparse

from super_agents.aerospace.insiders import fetch_and_parse_form4s
from super_agents.aerospace.watchlist import load_company_watchlist


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and parse recent Form 4 filings")
    parser.add_argument("--ticker", help="Ticker")
    parser.add_argument("--cik", help="CIK")
    parser.add_argument("--days", type=int, default=180, help="Lookback window in days")
    parser.add_argument("--watchlist", action="store_true", help="Run across the tracked watchlist")
    args = parser.parse_args()

    if args.watchlist:
        companies = load_company_watchlist()
        for company in companies:
            if not company.ticker:
                continue
            try:
                result = fetch_and_parse_form4s(ticker=company.ticker, days=args.days)
            except Exception as exc:
                print(f"{company.ticker}: failed ({exc})")
                continue
            print(
                f"{result['ticker']}: filings={result['filings_considered']} "
                f"transactions={len(result['records'])}"
            )
            print(result["output_path"])
        return

    if not args.ticker and not args.cik:
        raise SystemExit("Provide --ticker, --cik, or --watchlist.")

    result = fetch_and_parse_form4s(ticker=args.ticker, cik=args.cik, days=args.days)
    print(f"{result['ticker']}: filings={result['filings_considered']} transactions={len(result['records'])}")
    print(result["output_path"])


if __name__ == "__main__":
    main()
