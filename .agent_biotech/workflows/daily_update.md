---
description: Daily data update — pull FDA, check 8-Ks, refresh ClinicalTrials.gov, update catalyst calendar
---

# Daily Update Workflow

Run every weekday morning to keep the tracker current.

## Steps

1. **Pull FDA approvals and clearances**
// turbo
```bash
python .agent/skills/fda_tracker/scripts/fetch_drug_approvals.py --days 1
python .agent/skills/fda_tracker/scripts/fetch_device_clearances.py --days 1
```

2. **Check FDA advisory committee calendar updates**
// turbo
```bash
python .agent/skills/fda_tracker/scripts/fetch_advisory_calendar.py
```

3. **Check sponsor 8-Ks for regulatory disclosures**
   - Search EDGAR for 8-K filings from tracked companies filed in last 24 hours
   - Extract PDUFA dates, accepted filings, CRLs, topline data announcements
   - Tag as `source_type = "SEC"` and `source_confidence = "secondary"`

4. **Update ClinicalTrials.gov records**
   - For all tracked sponsors with active trials, run change detection
   - Flag status changes, date changes, and new results

5. **Refresh catalyst calendar**
// turbo
```bash
python .agent/skills/catalyst_calendar/scripts/build_calendar.py --days 90
```

6. **Tag source confidence**
   - Every new record must have `source_type` and `source_confidence` set
   - FDA-sourced data: `source_confidence = "primary"`
   - ClinicalTrials.gov: `source_confidence = "primary"`
   - SEC filings: `source_confidence = "secondary"`
   - Press releases: `source_confidence = "sponsor"`

7. **Generate daily summary**
   - Count new records by source type
   - List upcoming catalysts in next 7 days
   - Flag any sponsor-only milestones needing verification
