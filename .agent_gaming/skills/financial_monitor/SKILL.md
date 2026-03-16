---
name: financial_monitor
description: Calculate cash runway, milestone dependence, and dilution risk from SEC filings for publicly traded game studios
---

# Financial Monitor Skill

## Purpose

Reuse the cash-runway logic from the biotech tracker for studios that spend years burning cash before a single binary launch event.

## What to measure

- Cash plus short-term investments
- Quarterly operating burn
- Estimated runway months
- Going-concern language
- Dependence on publisher milestone receipts
- Delay sensitivity for the next major title

## Temporary implementation note

The existing SEC financial parsing prototypes in `.agent/skills/financial_monitor/scripts/`
are reusable at the filing layer and should be adapted next for gaming-specific
delay scenarios and milestone assumptions.

## Next implementation targets

- Add title-delay stress testing to runway outputs
- Add milestone-receipt assumptions by title
- Flag studios whose runway does not cover the next planned launch window
