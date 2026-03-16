"""Aerospace and defense tech agent blueprint package."""

from .awards import build_award_query_manifest, build_watchlist_manifests
from .dashboard import build_results_dashboard
from .budgets import parse_budget_pdf
from .calendar import build_program_calendar
from .faa import build_faa_query_manifest, fetch_faa_pages
from .financials import fetch_and_build_financial_snapshot, fetch_watchlist_financial_snapshots
from .insiders import fetch_and_parse_form4s
from .procurement import extract_procurement_signals
from .ranking import build_watchlist_ranking
from .sam import build_sam_query_manifest, fetch_sam_opportunity_pages
from .scorecards import build_budget_exposure_matches, build_company_scorecards
from .sec import fetch_and_cache_sec_filings
from .sbir import fetch_sbir_award_pages
from .trl import build_trl_signal, validate_trl_level
from .usaspending import fetch_award_search_pages, match_awards_to_companies, normalize_award_match
from .watchlist import load_company_watchlist, load_system_watchlist

__all__ = [
    "__version__",
    "build_award_query_manifest",
    "build_budget_exposure_matches",
    "build_program_calendar",
    "build_company_scorecards",
    "build_faa_query_manifest",
    "build_sam_query_manifest",
    "build_results_dashboard",
    "build_trl_signal",
    "build_watchlist_ranking",
    "build_watchlist_manifests",
    "extract_procurement_signals",
    "fetch_award_search_pages",
    "fetch_and_cache_sec_filings",
    "fetch_and_build_financial_snapshot",
    "fetch_faa_pages",
    "fetch_sam_opportunity_pages",
    "fetch_sbir_award_pages",
    "fetch_watchlist_financial_snapshots",
    "fetch_and_parse_form4s",
    "load_company_watchlist",
    "load_system_watchlist",
    "match_awards_to_companies",
    "normalize_award_match",
    "parse_budget_pdf",
    "validate_trl_level",
]

__version__ = "0.1.0"
