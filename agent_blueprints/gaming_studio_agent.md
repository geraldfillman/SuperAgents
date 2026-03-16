# Gaming Studio Agent Blueprint

This document outlines how to adapt the "Asset-First" architecture of the Biotech Agent to track publicly traded game development studios (especially Small/Mid-cap console and PC developers like CD Projekt, Starbreeze, or tinyBuild).

Game developers spend 3 to 5 years building a single product, burning cash continuously until a binary launch day that determines the company's survival and establishes a multi-year revenue tail.

## Key Folder / Skill Mapping

### 1. Financial Runway Monitor (Reuse exactly)
Studios without "games as a service" recurring revenue face massive liquidity gaps between major releases.
*   **Path Reference to Copy:** `.agent/skills/financial_monitor`
*   **Action:** If a game is delayed by 6 months, calculate exactly whether the studio will need to issue shares (dilution) to keep the lights on and pay developers. 

### 2. The SEC Filings Parser (Modify broadly)
*   **Path Reference to Copy:** `.agent/skills/sec_filings_parser`
*   **Action:** Instead of looking for clinical milestones, the parser must look for "Publisher Milestone Payments." Many studios receive cash injections from publishers (like EA, Xbox, or Sony) upon delivering the Alpha or Beta build. Missing a milestone halts the cash flow.

### 3. The FDA Tracker / ClinicalTrials.gov ➔ Platform Certification Tracker (Needs Rewrite)
Instead of FDA clearance, a game needs certification from platforms (Sony QA, Xbox Certification, Nintendo Lotcheck) and rating boards (ESRB, PEGI).
*   **Path Reference to replace:** `.agent/skills/fda_tracker`
*   **New Design (`certification_tracker`):** 
    *   Scrape regional rating boards (like the Korean Game Rating Board or US ESRB). A rating appearing on the registry is a leading indicator that the game is "content complete" and a launch date announcement is imminent.

### 4. Catalyst Calendar ➔ Launch Date & Wishlist Momentum (Needs Rewrite)
A drug's clinical data is binary. A game's launch success is predicted by measurable, pre-release momentum.
*   **Path Reference to replace:** `.agent/skills/clinicaltrials_scraper`
*   **New Design (`steam_api_scraper`):** 
    *   Use SteamDB or the Steam Web API to scrape daily "Wishlist Additions" and "Follower Counts." 
    *   Plot the trajectory of wishlists leading up to launch week. A spike in wishlists correlates with higher Day 1 sales and minimizes revenue risk.

### 5. Product Quality / Postmarketing ➔ Metacritic & Concurrent Player Monitor (New)
After launch, the asset's value is immediately visible.
*   **New Design (`engagement_monitor`):** 
    *   Track the Day 1 Metacritic score (replaces the biotech "quality rubric").
    *   Track Steam Concurrent Players over the first 30 days to measure "stickiness" and the likelihood of high-margin DLC sales.

## Database Schema Adaptation
*   **`products` table ➔ `titles` table:** `game_title`, `genre`, `engine` (UE5, Unity), `publisher`, `status` (Pre-production, Alpha, Beta, Gold Master, Launched).
*   **`clinical_trials` table ➔ `wishlists` table:** `steam_app_id`, `date`, `follower_count`, `wishlist_rank`.
