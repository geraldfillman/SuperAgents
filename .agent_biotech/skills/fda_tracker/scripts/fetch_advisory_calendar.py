"""
FDA Tracker — Fetch Advisory Committee Calendar
Parses the FDA Advisory Committee Calendar page for upcoming meetings.
"""

import json
import httpx
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

RAW_DIR = Path("data/raw/fda/advisory_calendar")
CALENDAR_URL = "https://www.fda.gov/advisory-committees/advisory-committee-calendar"


def fetch_advisory_calendar() -> list[dict]:
    """Scrape the FDA Advisory Committee Calendar for upcoming meetings."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    response = httpx.get(CALENDAR_URL, timeout=30, follow_redirects=True)
    response.raise_for_status()

    # Save raw HTML
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"calendar_{timestamp}.html"
    raw_path.write_text(response.text)

    return _parse_calendar(response.text)


def _parse_calendar(html: str) -> list[dict]:
    """Parse advisory committee calendar HTML into structured records."""
    soup = BeautifulSoup(html, "lxml")
    meetings = []

    # FDA calendar typically uses table or list-based layouts
    # This parser handles the common table format
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:  # Skip header
            cells = row.find_all("td")
            if len(cells) >= 3:
                meeting = {
                    "committee_name": cells[0].get_text(strip=True) if len(cells) > 0 else "",
                    "meeting_date": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                    "topic": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                    "materials_posted": False,
                    "source_url": CALENDAR_URL,
                    "source_type": "FDA",
                    "source_confidence": "primary",
                    "fetched_at": datetime.now().isoformat(),
                }

                # Check for materials links
                links = row.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "materials" in href.lower() or "briefing" in href.lower():
                        meeting["materials_posted"] = True
                        meeting["materials_url"] = href

                meetings.append(meeting)

    return meetings


if __name__ == "__main__":
    meetings = fetch_advisory_calendar()
    print(f"Found {len(meetings)} advisory committee meetings")
    for m in meetings[:5]:
        print(f"  {m['meeting_date']} | {m['committee_name']} | {m['topic'][:60]}")
