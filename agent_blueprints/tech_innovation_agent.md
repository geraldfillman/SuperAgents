# Tech Innovation Agent Blueprint

This document outlines how to adapt the "Asset-First" architecture of the Biotech Agent to track fast-moving, high-growth technology companies across hardware (AI semiconductors, robotics) and software (foundational models, developer tools, SaaS).

In tech, the velocity is extreme. A "product" might be an AI chip architecture or an LLM release that makes or breaks the company's valuation against incumbents.

## Key Folder / Skill Mapping

### 1. Financial Runway Monitor (Reuse exactly)
Cash burn remains deeply relevant for hardware startups (fabless semi designers, robotics) and foundational AI model builders spending billions on GPU compute clusters.
*   **Path Reference to Copy:** `.agent/skills/financial_monitor`
*   **Action:** Continue calculating the cash depletion runway leading up to major hardware tape-outs or cloud scaling milestones.

### 2. The Insider Tracker (Reuse exactly)
*   **Path Reference to Copy:** `.agent/skills/insider_tracker`
*   **Action:** Copy the `monitor_form4.py` script. Executive stock selling right before a delayed hardware launch or a missed AI benchmark is a critical signal.

### 3. Medical Conference Scraper ➔ Industry Event / Keynote Parser (Modify heavily)
Tech companies do not wait for peer-reviewed journals to drop data. They drop it at GTC, CES, AWS re:Invent, or proprietary developer days.
*   **Path Reference to modify:** `.agent/skills/conference_scraper`
*   **New Design (`keynote_parser`):** 
    *   Track the timelines of major tech events. Parse the keynote transcripts and press releases for product announcements, spec reveals, or partnership integrations.

### 4. ClinicalTrials Scraper ➔ Benchmark & Developer Adoption Scraper (Needs Rewrite)
Instead of tracking patient enrollment, you track objective technical benchmarks and developer mindshare.
*   **Path Reference to replace:** `.agent/skills/clinicaltrials_scraper`
*   **New Design (`benchmark_scraper`):** 
    *   For AI/Semi: Scrape MLPerf scores, Hugging Face leaderboards, or specific model evaluation benchmarks (e.g., MMLU, GSM8K).
    *   For Dev Tools: Scrape GitHub stars, fork velocity, or NPM weekly downloads to track grassroots developer adoption acting as a leading indicator of SaaS revenue.

### 5. The FDA Tracker ➔ Hardware Tape-Out / Product Launch Tracker (Needs Rewrite)
Building physical technology mirrors the rigidity of drug development. 
*   **Path Reference to replace:** `.agent/skills/fda_tracker`
*   **New Design (`product_lifecycle_tracker`):** 
    *   For hardware, track the phases: Architecture Reveal ➔ Tape-Out ➔ Silicon Yield ➔ General Availability (GA). A failed tape-out is the equivalent of an FDA Complete Response Letter (CRL).

## Database Schema Adaptation
*   **`products` table:** `product_name`, `category` (LLM, NPU Chip, SaaS Tool), `current_phase` (Alpha, Beta, Tape-Out, GA).
*   **`metric_scores` table (New):** Replaces `regulatory_events`. Tracks historical performance integers (e.g., "Inference tokens/sec" or "GitHub Star Count").
