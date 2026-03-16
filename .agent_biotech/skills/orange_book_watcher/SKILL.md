---
name: orange_book_watcher
description: Track patent exclusivity cliffs and generic defense per product using the FDA Orange Book.
---

# Orange Book Watcher

## Purpose
Knowing exactly when a small-cap's flagship drug faces generic competition allows analysts to mathematically map out its "terminal value." This skill monitors FDA Orange Book data to track active patents and exclusivity periods for approved drugs.

## Data Sources
- **FDA Orange Book**: Approved Drug Products with Therapeutic Equivalence Evaluations.

## Scripts Provided

### `scripts/fetch_patents.py`
Simulates querying Orange Book patent/exclusivity data for a specific drug. In production, this would query the openFDA drug/ndc index or download the Orange Book zip files.
**Usage:**
```bash
python .agent/skills/orange_book_watcher/scripts/fetch_patents.py --active-ingredient "diazepam"
```

## Setup & Rules
1. Save output to `data/processed/patents/`.
