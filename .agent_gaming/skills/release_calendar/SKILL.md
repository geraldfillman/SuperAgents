---
name: release_calendar
description: Build and refresh the rolling gaming catalyst calendar
---

# Release Calendar Skill

## Purpose

Build a rolling calendar from upcoming launches, certification signals, publisher
milestones, and other title-level events.

## Inputs

- `release_events`
- `publisher_milestones`
- `certifications`
- `storefront_metrics`
- `gaming_sec_catalysts`

## Scripts

### `scripts/build_calendar.py`

Merge normalized processed JSON records into a single sorted calendar.
