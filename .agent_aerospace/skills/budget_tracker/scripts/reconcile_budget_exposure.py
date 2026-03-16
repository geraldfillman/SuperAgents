"""Reconcile budget lines to tracked systems and build company scorecards."""

from __future__ import annotations

import argparse

from adt_agent.scorecards import build_company_scorecards, save_budget_exposure_matches, save_company_scorecards
from adt_agent.watchlist import load_company_watchlist, load_system_watchlist


def main() -> None:
    parser = argparse.ArgumentParser(description="Build budget exposure matches and company scorecards")
    parser.add_argument("--ticker", help="Optional ticker filter")
    parser.add_argument("--min-budget-score", type=float, default=0.35, help="Minimum heuristic score for budget candidates")
    args = parser.parse_args()

    companies = load_company_watchlist()
    systems = load_system_watchlist()
    if args.ticker:
        ticker = args.ticker.upper()
        companies = [company for company in companies if company.ticker.upper() == ticker]
        systems = [system for system in systems if system.ticker.upper() == ticker]
        if not companies:
            raise SystemExit(f"No watchlist company found for ticker {ticker}.")

    bundle = build_company_scorecards(
        companies=companies,
        systems=systems,
        min_budget_score=args.min_budget_score,
    )
    label = args.ticker or "watchlist"
    matches_path = save_budget_exposure_matches(bundle["budget_exposure_matches"], label=label)
    scorecards_path = save_company_scorecards(bundle, label=label)

    print(
        f"Built {len(bundle['budget_exposure_matches'])} budget exposure match(es) "
        f"across {len(bundle['company_scorecards'])} company scorecard(s)"
    )
    print(matches_path)
    print(scorecards_path)


if __name__ == "__main__":
    main()
