"""
Conference Scraper — Scrape Abstracts
Mocks the scraping of major medical conferences for specific keywords.
(A full production version requires custom parsers for ASCO, ESMO, ASH, etc.)
"""

import json
from pathlib import Path
from datetime import datetime
import pandas as pd

OUT_DIR = Path("data/processed/conferences")

# Mock database of recent/upcoming conferences
CONFERENCES = [
    {"name": "ASCO 2026", "date": "2026-05-29", "topic": "Oncology"},
    {"name": "ESMO 2026", "date": "2026-09-18", "topic": "Oncology"},
    {"name": "ASH 2026", "date": "2026-12-05", "topic": "Hematology"},
    {"name": "JPM Healthcare", "date": "2026-01-12", "topic": "General"}
]

def search_conferences(keywords: list[str]):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    
    # Simulate finding matches
    for keyword in keywords:
        for conf in CONFERENCES:
            # We mock a finding: every keyword gets a hit at a random conference
            if keyword.lower() in ["ziftomenib", "barzolvolimab", "aqst", "cldx"]:
                results.append({
                    "keyword_matched": keyword,
                    "conference_name": conf["name"],
                    "conference_date": conf["date"],
                    "abstract_title": f"Phase 2 interim outcomes of {keyword} in target patient population",
                    "presentation_type": "Poster Session",
                    "source_url": f"https://mock-conference-spidertrap.com/abstracts/{keyword.lower()}"
                })
                break # Just find one for the mock

    if results:
        df = pd.DataFrame(results)
        out_file = OUT_DIR / f"abstracts_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(out_file, index=False)
        print(f"🔎 FOUND {len(results)} RELEVANT ABSTRACTS 🔎")
        for res in results:
            print(f"[{res['conference_name']}] {res['abstract_title']}")
    else:
        print(f"No abstracts found for keywords: {', '.join(keywords)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", type=str, required=True, help="Comma-separated keywords/tickers")
    args = parser.parse_args()
    
    keys = [k.strip() for k in args.keywords.split(",")]
    search_conferences(keys)
