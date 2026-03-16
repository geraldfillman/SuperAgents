---
name: product_scoring
description: Score products on 10 evidence/regulatory dimensions and compute derived risk flags
---

# Product Scoring Skill

## Purpose
Apply a standardized scoring model to biotech products based on **evidence quality and regulatory setup**, not stock price.

## Scoring Dimensions (1–5 scale)

| Dimension | What it measures |
|-----------|-----------------|
| Evidence Maturity | How far the clinical evidence has progressed |
| Endpoint Clarity | Is the primary endpoint well-defined and accepted by FDA? |
| Trial Design Quality | Randomized, controlled, adequate sample size? |
| Regulatory Advantage | Does it have designations (BTD, Fast Track, Orphan, Priority)? |
| Unmet Need Severity | How severe is the disease with how few alternatives? |
| Mechanism Plausibility | Is the MOA supported by biological rationale and prior data? |
| Manufacturing Complexity Risk | CMC risk (cell therapy > small molecule) |
| Safety Uncertainty | Known safety signals or class effects? |
| Sponsor Disclosure Quality | Transparent data sharing, consistent messaging? |
| Near-term Catalyst Density | How many meaningful milestones in the next 6 months? |

## Derived Flags

| Flag | Logic |
|------|-------|
| `binary_event_risk` | High if single catalyst determines product fate |
| `regulatory_visibility` | High if FDA has official action date or accepted submission |
| `science_readthrough_value` | High if mechanism has implications beyond lead indication |
| `crowded_indication_penalty` | High if >5 competitors in same indication/phase |
| `approval_path_complexity` | High if novel endpoint, first-in-class, or combo requirements |

## Scripts

### `scripts/score_product.py`
Interactive or batch scoring. Accepts product data and returns composite scores + derived flags.

## Usage
```bash
# Score a single product interactively
python .agent/skills/product_scoring/scripts/score_product.py --product-id PROD_001

# Batch score all active products
python .agent/skills/product_scoring/scripts/score_product.py --batch --active-only
```
