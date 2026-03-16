---
description: Monthly reconciliation — verify against SEC filings, archive discontinued, rebuild indication coverage
---

# Monthly Reconciliation Workflow

Run on the 1st of each month for deep data quality and coverage analysis.

## Steps

1. **Reconcile product records against SEC filings**
   - Pull latest 10-Q / 10-K / 20-F for all tracked companies
   - Compare disclosed pipeline against `products` table
   - Flag discrepancies: missing products, status mismatches, new assets
   - Update `regulatory_events` with any newly disclosed milestones

2. **Archive discontinued assets**
   - Identify products with:
     - Status = "Withdrawn / discontinued / terminated"
     - No updates in 90+ days
     - Sponsor has announced discontinuation
   - Set `active = false` in `products` table
   - Preserve full event history (never delete)

3. **Rebuild indication-level coverage**
   - Count active products per indication
   - Compare against target distribution (from Biotech.md):
     - 30% oncology/hematology
     - 15% rare disease
     - 10% CNS
     - 10% immunology
     - 10% infectious disease
     - 10% devices/diagnostics
     - 15% flexible opportunistic
   - Flag overconcentration and gaps

4. **Summarize regulatory outcomes**
   - Wins: approvals, clearances, positive data readouts
   - Misses: CRLs, failed endpoints, safety holds
   - Slips: delayed PDUFA dates, pushed completion dates
   - Group by modality

5. **Data quality deep audit**
   - Check all source URLs are still accessible
   - Verify product name aliases are tracked
   - Confirm company mergers/splits have maintained product continuity
   - Flag records with `sponsor_disclosed_target_date` that have passed

6. **Generate monthly report**
   - Executive summary of regulatory landscape
   - Portfolio-level statistics
   - Data quality metrics
   - Indication coverage heatmap
   - Recommended actions for next month
