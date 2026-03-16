---
name: company_screener
description: Screen and discover new micro/small-cap biotech, pharma, and medtech companies from exchange listings
---

# Company Screener Skill

## Purpose
Discover and add new publicly traded biotech/pharma/medtech companies to the tracker universe.

## Company Universe (from Biotech.md)
- Nasdaq, NYSE, NYSE American
- OTCQB / OTCQX / select OTC names

## Included Categories
- Oncology biotech
- Rare disease biotech
- CNS / neuro
- Immunology / inflammation
- Infectious disease
- Metabolic / endocrine
- Cell therapy, Gene therapy
- RNA / oligo / antisense
- Radiopharma
- Diagnostics, Medical devices
- Digital therapeutics
- Specialty pharma with active regulatory pipelines

## Excluded
- Pure services businesses
- Providers focused on margin / roll-up / reimbursement arbitrage
- Mature large-cap pharma (unless context needed)

## Market Cap Buckets
| Bucket | Range |
|--------|-------|
| nano | < $50M |
| micro | $50M – $300M |
| small | $300M – $2B |
| mid | $2B – $10B |

## Scripts

### `scripts/screen_companies.py`
Screen for new companies to add. Uses SEC EDGAR and financial data APIs to identify:
- Recently IPO'd biotech/pharma/medtech
- Companies with recent FDA submissions visible in EDGAR
- Companies below market cap thresholds with active clinical programs

## Usage
```bash
# Screen for new companies
python .agent/skills/company_screener/scripts/screen_companies.py

# Screen with market cap filter
python .agent/skills/company_screener/scripts/screen_companies.py --max-market-cap 2B --sector biotech
```
