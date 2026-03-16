# Clean Energy & Pre-Revenue Mining Agent Blueprint

This document outlines how to adapt the "Asset-First" architecture of the Biotech Agent to track junior mining, critical minerals, and pre-revenue clean energy technology companies. 

In this sector, companies burn cash for years before generating revenue. The "Product" is the mining site (e.g., a lithium deposit) or the battery prototype. The catalysts are geological feasibility studies and environmental permitting approvals. 

## Key Folder / Skill Mapping

### 1. Financial Runway Monitor (Reuse exactly)
The most critical aspect of a pre-revenue mining company is dilution. You can reuse the Biotech Agent's financial monitor without any logical changes.
*   **Path Reference to Copy:** `.agent/skills/financial_monitor`
*   **Why:** You need `fetch_financials.py` to calculate the cash burn rate from 10-Q/10-K filings, and `flag_offerings.py` to detect shelf registrations (S-3) or At-The-Market (ATM) offerings. 

### 2. The Insider Tracker (Reuse exactly)
Monitoring Form 4s for open-market buying by mining CEOs is highly predictive before major drilling results are announced. 
*   **Path Reference to Copy:** `.agent/skills/insider_tracker`
*   **Why:** Operates exactly the same; just point the `monitor_form4.py` script to a new list of mining and energy CIKs.

### 3. The FDA Tracker ➔ Environmental Permitting Scraper (Needs Rewrite)
You no longer care about the FDA. You care about the BLM (Bureau of Land Management), EPA, and state-level registries.
*   **Path Reference to replace:** `.agent/skills/fda_tracker`
*   **New Design (`permit_scraper`):** 
    *   Query federal/state environmental databases to track the status of Draft Environmental Impact Statements (DEIS) or Final Records of Decision (ROD). These are your new "PDUFA" binary approval events.

### 4. ClinicalTrials Scraper ➔ Drill Result / Technical Report Parser (Needs Rewrite)
Instead of clinical trial endpoints, you are looking for grade and tonnage. Standardized Canadian (NI 43-101) or Australian (JORC) technical reports are required by law, similar to clinical trial reporting.
*   **Path Reference to replace:** `.agent/skills/clinicaltrials_scraper`
*   **New Design (`technical_report_parser`):** 
    *   Parse SEDAR+ (Canada) or SEC EDGAR filings for Preliminary Economic Assessments (PEA), Pre-Feasibility Studies (PFS), or Bankable Feasibility Studies (BFS). 
    *   Extract key metrics: Net Present Value (NPV), Internal Rate of Return (IRR), and Initial Capital Expenditure (CapEx).

## Database Schema Adaptation
Instead of the `products` table, you need a `projects` table:
*   **`projects` table:** `project_name`, `commodity` (e.g., Lithium, Copper), `location`, `stage` (e.g., Exploration, PEA, PFS, Permitted, Construction).
*   **`resource_estimates` table:** Maps to the clinical trials table. Stores `measured_tonnes`, `indicated_tonnes`, `inferred_tonnes`, and `grade`.
