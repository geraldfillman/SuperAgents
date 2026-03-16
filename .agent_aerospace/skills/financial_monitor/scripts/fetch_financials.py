"""Fetch normalized financial snapshots from SEC companyfacts."""

from __future__ import annotations

import argparse

from adt_agent.financials import fetch_and_build_financial_snapshot, fetch_watchlist_financial_snapshots
from adt_agent.watchlist import load_company_watchlist


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch SEC companyfacts and estimate runway")
    parser.add_argument("--ticker", help="Ticker")
    parser.add_argument("--cik", help="CIK")
    parser.add_argument("--watchlist", action="store_true", help="Run across the tracked watchlist")
    parser.add_argument("--only-missing", action="store_true", help="Skip companies that already have a saved snapshot")
    parser.add_argument("--limit", type=int, help="Optional cap on watchlist companies to fetch")
    parser.add_argument("--pause-seconds", type=float, default=0.2, help="Pause between SEC requests in watchlist mode")
    args = parser.parse_args()

    if args.watchlist:
        companies = load_company_watchlist()
        summary = fetch_watchlist_financial_snapshots(
            companies=companies,
            only_missing=args.only_missing,
            limit=args.limit,
            pause_seconds=max(args.pause_seconds, 0.0),
        )
        for snapshot in summary["snapshots"]:
            print(
                f"{snapshot['ticker']}: cash={snapshot['total_cash_millions']}M "
                f"burn={snapshot['quarterly_burn_millions']}M runway={snapshot['est_runway_months']} months"
            )
            print(snapshot["output_path"])
        for skipped in summary["skipped"]:
            suffix = f" report_date={skipped['report_date']}" if skipped.get("report_date") else ""
            print(f"{skipped['ticker']}: skipped ({skipped['reason']}){suffix}")
        for failure in summary["failures"]:
            print(f"{failure['ticker']}: failed ({failure['error']})")
        print(
            "summary: "
            f"requested={summary['requested_companies']} "
            f"saved={summary['saved_snapshots']} "
            f"skipped={summary['skipped_count']} "
            f"failed={summary['failure_count']}"
        )
        return

    if not args.ticker and not args.cik:
        raise SystemExit("Provide --ticker, --cik, or --watchlist.")

    snapshot = fetch_and_build_financial_snapshot(ticker=args.ticker, cik=args.cik)
    print(
        f"{snapshot['ticker']}: cash={snapshot['total_cash_millions']}M "
        f"burn={snapshot['quarterly_burn_millions']}M runway={snapshot['est_runway_months']} months"
    )
    print(snapshot["output_path"])


if __name__ == "__main__":
    main()
