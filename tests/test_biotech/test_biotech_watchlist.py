"""Tests for biotech sector watchlist helpers."""

from super_agents.biotech.watchlist import (
    find_company,
    load_company_watchlist,
    load_product_watchlist,
)


def test_biotech_company_watchlist_loads_seed_records():
    companies = load_company_watchlist()

    assert len(companies) >= 5
    assert companies[0].ticker
    assert find_company(ticker="AQST", companies=companies).company_name == "Aquestive Therapeutics"


def test_biotech_product_watchlist_loads_seed_records():
    products = load_product_watchlist()

    names = {product.product_name for product in products}
    assert "Libervant" in names
    assert "Barzolvolimab" in names
