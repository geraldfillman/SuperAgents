---
name: engagement_monitor
description: Track launch quality and post-launch engagement for released titles
---

# Engagement Monitor Skill

## Purpose

Measure how a launched title is performing once quality and player behavior become visible.

## Signals to track

- Day 1 critic score snapshots
- Steam current-player counts
- 24-hour and all-time peaks when available
- Review sentiment changes over the first 30 days

## Scripts

### `scripts/fetch_engagement_metrics.py`

Fetch public Steam concurrency metrics for one app ID or a batch file of app IDs
and save normalized records under `data/processed/engagement_metrics/`.
