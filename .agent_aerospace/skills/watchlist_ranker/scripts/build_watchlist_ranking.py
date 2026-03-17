"""Build a ranked watchlist from current company scorecards."""

from __future__ import annotations

import argparse

from super_agents.aerospace.ranking import build_watchlist_ranking, save_watchlist_ranking
from super_agents.aerospace.scorecards import build_company_scorecards, save_company_scorecards
from super_agents.aerospace.watchlist import load_company_watchlist, load_system_watchlist


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ranked watchlist")
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

    scorecard_bundle = build_company_scorecards(
        companies=companies,
        systems=systems,
        min_budget_score=args.min_budget_score,
    )
    ranking_bundle = build_watchlist_ranking(scorecard_bundle=scorecard_bundle, min_budget_score=args.min_budget_score)
    label = args.ticker or "watchlist"
    scorecards_path = save_company_scorecards(scorecard_bundle, label=label)
    out_path = save_watchlist_ranking(ranking_bundle, label=label)

    print(f"Ranked {len(ranking_bundle['rankings'])} company record(s)")
    print(scorecards_path)
    print(out_path)


if __name__ == "__main__":
    main()
