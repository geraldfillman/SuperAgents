"""Tests for fintech sector watchlist helpers."""

from super_agents.fintech.watchlist import find_company, load_company_watchlist


def test_fintech_company_watchlist_loads_seed_records():
    companies = load_company_watchlist()

    assert len(companies) >= 5
    assert companies[0].ticker
    assert find_company(ticker="SOFI", companies=companies).company_name == "SoFi Technologies"


def test_fintech_company_watchlist_matches_by_company_name():
    company = find_company(company_name="PayPal Holdings")

    assert company is not None
    assert company.ticker == "PYPL"
