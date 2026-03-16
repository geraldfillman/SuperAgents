# Aerospace & Defense Tech Agent Blueprint

This document outlines how to adapt the "Asset-First" architecture of the Biotech Agent to track emerging, publicly traded defense technology companies, satellite manufacturers, and drone builders. 

In this sector, products are hardware systems or software platforms whose survival completely depends on government procurement contracts and successful testing milestones.

## Key Folder / Skill Mapping

### 1. Financial Runway Monitor (Reuse exactly)
Monitoring cash burn is vital for defense startups attempting to bridge the "Valley of Death" between a prototype and a massive Program of Record (PoR) contract.
*   **Path Reference to Copy:** `.agent/skills/financial_monitor`
*   **Why:** You need to monitor 10-Q/10-K filings to compute exactly how many quarters a company can survive if a specific DoD contract is delayed by Congressional budget gridlock (Continuing Resolutions). S-3 dilution flags are critical here.

### 2. The Insider Tracker (Reuse exactly)
*   **Path Reference to Copy:** `.agent/skills/insider_tracker`
*   **Why:** Executive insider buying preceding the announcement of a classified contract or a successful demonstrator flight is a massive tell. Point the `monitor_form4.py` script at defense CIKs.

### 3. The SEC Filings Parser (Modify logic)
While the Biotech SEC parser looked for things like "PDUFA" or "Phase 3 Topline", the defense parser needs to look for "Phase III SBIR", "Other Transaction Authority (OTA)", or "Indefinite Delivery/Indefinite Quantity (IDIQ)".
*   **Path Reference to Copy:** `.agent/skills/sec_filings_parser`
*   **Action:** Update the keyword extraction dictionaries in `extract_catalysts.py` to catch defense procurement milestones.

### 4. The FDA Tracker ➔ SAM.gov Scraper (Needs Rewrite)
You no longer care about FDA approvals; you care about government contract awards.
*   **Path Reference to replace:** `.agent/skills/fda_tracker`
*   **New Design (`award_tracker`):** 
    *   Query SAM.gov (System for Award Management) APIs or parse DoD daily contract award announcements. Look for the company's CAGE code or Unique Entity ID instead of an NDA number.

### 5. ClinicalTrials Scraper ➔ TRL / Test Flight Tracker (Needs Rewrite)
Instead of clinical phases (Phase 1/2/3), the Department of Defense uses Technology Readiness Levels (TRL 1 through 9).
*   **Path Reference to replace:** `.agent/skills/clinicaltrials_scraper`
*   **New Design (`trl_tracker`):** 
    *   Parse press releases and technical blog posts to assign a TRL score to each defense product. An upgrade from TRL 6 (prototype demonstation) to TRL 8 (system integrated) is the equivalent of a successful Phase 3 trial.

## Database Schema Adaptation
*   **`products` table ➔ `systems` table:** `system_name`, `domain` (Space, Cyber, Air, Sea, Land), `trl_level`.
*   **`clinical_trials` table ➔ `contracts` table:** `contract_id`, `agency` (e.g., DARPA, Space Force), `ceiling_value`, `period_of_performance`.
