---
name: conference_scraper
description: Scrapes major medical conference databases (ASCO, ESMO, ASH) to catch abstract titles and data presentations for tracked micro-caps.
---

# Medical Conference Scraper

## Purpose
Companies often issue press releases weeks after a major medical conference abstract is actually published online. This skill proactively hunts for tracked tickers and product aliases in the abstract archives of major symposia (e.g., ASCO, ESMO, JPM, ASH) to catch hidden data presentations.

## Data Sources
- Publicly accessible abstract search portals for medical conferences.

## Scripts Provided

### `scripts/scrape_abstracts.py`
Simulates finding conference abstracts containing specific keywords. In reality, this would require custom scrapers (using BeautifulSoup/Selenium) for each conference's unique portal.
**Usage:**
```bash
python .agent/skills/conference_scraper/scripts/scrape_abstracts.py --keywords "Ziftomenib,Barzolvolimab"
```

## Setup & Rules
1. Save output to `data/processed/conferences/`.
