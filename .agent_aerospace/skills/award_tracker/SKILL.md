# Award Tracker

Purpose: track contract awards, modifications, and procurement vehicles tied to a company or system.

Inputs:

- company name
- ticker
- CAGE code or UEID when available
- agency filter

Outputs:

- normalized `contract_awards` records
- source confidence tags
- links back to `companies` and `systems`
- saved query manifests when live access is unavailable or not desired

Priority signals:

- new awards
- ceiling value increases
- transition from prototype to production vehicle
- contract term extensions

Notes:

- use manifest mode for offline planning
- use `--live` mode for USAspending-backed fetches
- contract awards and IDV vehicles are queried separately because USAspending does not allow mixed award-type groups in one search request
