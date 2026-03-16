---
name: storefront_monitor
description: Collect public storefront metadata and momentum proxies for tracked titles
---

# Storefront Monitor Skill

## Purpose

Track public storefront metadata for pre-launch and launched titles without assuming
partner-only analytics access.

## Public v1 coverage

- Steam app metadata
- Public release-date changes
- Tags, supported platforms, and publisher/developer labels
- Review-count and review-score fields when exposed

## Scripts

### `scripts/fetch_storefront_metrics.py`

Fetch public Steam storefront snapshots for one app ID or a batch file of app IDs
and save normalized records under `data/processed/storefront_metrics/`.

## Notes

- Do not assume public access to daily wishlist additions
- Keep `follower_count` and `wishlist_rank` nullable until a compliant source is available
