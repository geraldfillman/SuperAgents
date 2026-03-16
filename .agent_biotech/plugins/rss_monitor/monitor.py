"""
RSS Monitor Plugin — Watch FDA feeds for new entries.
"""

import os
import json
import feedparser
from datetime import datetime
from pathlib import Path

RAW_DIR = Path("data/raw/rss")


def check_feeds(feed_configs: list[dict]) -> list[dict]:
    """
    Check RSS feeds for new entries.

    Args:
        feed_configs: List of feed configs from plugin.yaml

    Returns:
        List of new entries found
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_entries = []
    for feed_config in feed_configs:
        url = feed_config.get("url", "")
        category = feed_config.get("category", "unknown")

        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                parsed = {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", ""),
                    "category": category,
                    "feed_name": feed_config.get("name", ""),
                    "fetched_at": datetime.now().isoformat(),
                }
                all_entries.append(parsed)
        except Exception as e:
            print(f"Error fetching {url}: {e}")

    # Save raw entries
    if all_entries:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = RAW_DIR / f"rss_entries_{timestamp}.json"
        out_path.write_text(json.dumps(all_entries, indent=2))

    return all_entries


def filter_new_entries(entries: list[dict], seen_file: str = "data/processed/rss_seen.json") -> list[dict]:
    """Filter out entries we've already processed."""
    seen_path = Path(seen_file)
    seen_links = set()

    if seen_path.exists():
        seen_links = set(json.loads(seen_path.read_text()))

    new_entries = [e for e in entries if e.get("link") not in seen_links]

    # Update seen set
    seen_links.update(e.get("link", "") for e in entries)
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(list(seen_links), indent=2))

    return new_entries


if __name__ == "__main__":
    # Example usage
    feeds = [
        {"name": "fda_test", "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds", "category": "test"},
    ]
    entries = check_feeds(feeds)
    print(f"Found {len(entries)} RSS entries")
