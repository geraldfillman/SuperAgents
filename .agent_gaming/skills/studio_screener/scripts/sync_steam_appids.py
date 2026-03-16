"""
Sync Steam app IDs from tracked studios and optionally discover missing IDs.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.gaming.io_utils import write_json
from super_agents.gaming.paths import (
    DEFAULT_APPIDS_FILE,
    DEFAULT_TRACKED_FILE,
    STUDIO_SCREENER_DIR,
    ensure_gaming_directory,
)
from super_agents.gaming.watchlist import build_tracked_studios_payload

INPUT_PATH = DEFAULT_TRACKED_FILE
APPIDS_PATH = DEFAULT_APPIDS_FILE
SUGGESTIONS_DIR = STUDIO_SCREENER_DIR
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch"


def _normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _load_records(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("Tracked studios file must contain a JSON array or object")
    return [item for item in payload if isinstance(item, dict)]


def _iter_titles(records: list[dict]) -> list[tuple[dict, dict]]:
    pairs: list[tuple[dict, dict]] = []
    for studio in records:
        titles = studio.get("titles", [])
        if not isinstance(titles, list):
            continue
        for title in titles:
            if isinstance(title, dict):
                pairs.append((studio, title))
    return pairs


def _search_steam(query: str, max_results: int = 5) -> list[dict]:
    response = httpx.get(
        STEAM_SEARCH_URL,
        params={
            "term": query,
            "l": "english",
            "cc": "US",
        },
        timeout=30,
        follow_redirects=True,
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items[:max_results] if isinstance(item, dict)]


def _score_match(query: str, result_name: str) -> float:
    query_norm = _normalize_title(query)
    result_norm = _normalize_title(result_name)
    if not query_norm or not result_norm:
        return 0.0
    if query_norm == result_norm:
        return 1.0
    if query_norm in result_norm or result_norm in query_norm:
        return 0.85
    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    result_tokens = set(re.findall(r"[a-z0-9]+", result_name.lower()))
    if not query_tokens:
        return 0.0
    overlap = len(query_tokens & result_tokens) / len(query_tokens)
    return round(min(0.79, overlap), 2)


def _build_suggestions(records: list[dict], max_results: int) -> list[dict]:
    suggestions: list[dict] = []
    for studio, title in _iter_titles(records):
        if title.get("steam_app_id"):
            continue

        game_title = str(title.get("game_title", "")).strip()
        if not game_title:
            continue

        try:
            results = _search_steam(game_title, max_results=max_results)
        except httpx.HTTPError as exc:
            suggestions.append(
                {
                    "company_name": studio.get("company_name", ""),
                    "ticker": studio.get("ticker", ""),
                    "game_title": game_title,
                    "status": "search_failed",
                    "error": str(exc),
                    "suggestions": [],
                }
            )
            continue

        ranked = []
        for result in results:
            result_name = str(result.get("name", ""))
            ranked.append(
                {
                    "steam_app_id": str(result.get("id", "")),
                    "name": result_name,
                    "score": _score_match(game_title, result_name),
                    "price": result.get("price", {}),
                }
            )
        ranked.sort(key=lambda item: item["score"], reverse=True)
        best = ranked[0] if ranked else None

        suggestions.append(
            {
                "company_name": studio.get("company_name", ""),
                "ticker": studio.get("ticker", ""),
                "game_title": game_title,
                "status": "suggested" if best else "no_results",
                "best_match": best,
                "suggestions": ranked,
            }
        )
    return suggestions


def _apply_exact_matches(records: list[dict], suggestions: list[dict], min_score: float) -> int:
    applied = 0
    best_by_title = {
        (entry.get("ticker", ""), entry.get("game_title", "")): entry.get("best_match")
        for entry in suggestions
        if entry.get("best_match")
    }

    for studio, title in _iter_titles(records):
        if title.get("steam_app_id"):
            continue
        key = (studio.get("ticker", ""), title.get("game_title", ""))
        best_match = best_by_title.get(key)
        if not best_match:
            continue
        if float(best_match.get("score", 0.0)) < min_score:
            continue
        title["steam_app_id"] = str(best_match.get("steam_app_id", ""))
        applied += 1

    return applied


def _write_appids(records: list[dict], path: Path) -> int:
    seen: set[str] = set()
    lines = [
        "# Generated from data/raw/gaming/studio_candidates.json",
        f"# Updated at {datetime.now(timezone.utc).isoformat()}",
    ]

    for studio, title in _iter_titles(records):
        raw_app_id = title.get("steam_app_id")
        if raw_app_id is None:
            continue
        app_id = str(raw_app_id).strip()
        if not app_id or app_id.lower() in {"none", "null", "nan"} or app_id in seen:
            continue
        seen.add(app_id)
        lines.append(f"# {studio.get('ticker', '')} | {title.get('game_title', '')}")
        lines.append(app_id)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(seen)


def _write_suggestions(suggestions: list[dict]) -> Path:
    ensure_gaming_directory(SUGGESTIONS_DIR)
    path = SUGGESTIONS_DIR / f"steam_appid_suggestions_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    write_json(path, suggestions)
    return path


def _write_input(records: list[dict], path: Path) -> None:
    write_json(path, records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Steam app IDs from tracked studios")
    parser.add_argument("--input", type=Path, default=INPUT_PATH, help="Tracked studios JSON file")
    parser.add_argument("--output", type=Path, default=APPIDS_PATH, help="Steam app ID output file")
    parser.add_argument("--discover-missing", action="store_true", help="Search Steam for titles missing steam_app_id")
    parser.add_argument("--write-input", action="store_true", help="Persist accepted matches back into the input JSON file")
    parser.add_argument("--min-score", type=float, default=1.0, help="Minimum match score required when applying suggestions")
    parser.add_argument("--max-results", type=int, default=5, help="Maximum Steam search results per missing title")
    args = parser.parse_args()

    if args.input.exists():
        records = _load_records(args.input)
    else:
        records = build_tracked_studios_payload(args.input)
        if not records:
            raise SystemExit(f"Tracked studios file not found and no seed payload was available: {args.input}")
        print(f"Tracked studios file not found at {args.input}. Using seed watchlist payload instead.")
    suggestions: list[dict] = []
    applied = 0

    if args.discover_missing:
        suggestions = _build_suggestions(records, max_results=args.max_results)
        suggestions_path = _write_suggestions(suggestions)
        print(f"Wrote Steam app ID suggestions to {suggestions_path}")
        if args.write_input:
            applied = _apply_exact_matches(records, suggestions, min_score=args.min_score)
            _write_input(records, args.input)
            print(f"Persisted {applied} title mappings back to {args.input}")

    total = _write_appids(records, args.output)
    print(f"Wrote {total} Steam app IDs to {args.output}")

    if suggestions:
        unresolved = sum(1 for item in suggestions if not item.get("best_match"))
        low_confidence = sum(
            1
            for item in suggestions
            if item.get("best_match") and float(item["best_match"].get("score", 0.0)) < args.min_score
        )
        print(f"Suggestions generated: {len(suggestions)} | unresolved: {unresolved} | below threshold: {low_confidence}")


if __name__ == "__main__":
    main()
