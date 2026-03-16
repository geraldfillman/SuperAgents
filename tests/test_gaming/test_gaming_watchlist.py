"""Tests for gaming sector watchlist helpers."""

from pathlib import Path

from super_agents.gaming.watchlist import (
    build_tracked_studios_payload,
    build_tracked_titles_by_appid,
    load_seed_appids,
    load_studio_watchlist,
)


def test_gaming_studio_watchlist_dedupes_company_rows():
    studios = load_studio_watchlist()

    tickers = {studio.ticker for studio in studios}
    assert len(studios) == len(tickers)
    assert {"EA", "TTWO", "CAPCOM"}.issubset(tickers)


def test_gaming_seed_watchlist_provides_batch_appids_and_title_mapping():
    appids = set(load_seed_appids())
    tracked_titles = build_tracked_titles_by_appid(Path("data/raw/gaming/studio_candidates.json"))

    assert {"1172470", "289070", "3357650"}.issubset(appids)
    assert tracked_titles["3357650"]["tracked_title"] == "PRAGMATA"


def test_gaming_seed_watchlist_builds_nested_payload():
    payload = build_tracked_studios_payload(Path("data/raw/gaming/studio_candidates.json"))

    assert payload
    capcom = next(studio for studio in payload if studio.get("ticker") == "CAPCOM")
    assert any(title.get("game_title") == "PRAGMATA" for title in capcom.get("titles", []))
