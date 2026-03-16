# FAA License Tracker

Purpose: monitor official FAA commercial space licensing and stakeholder-engagement pages for execution signals that matter before large contract history appears.

Inputs:

- tracked watchlist companies and systems
- optional ticker or manual company name
- optional custom FAA page URLs for focused monitoring

Outputs:

- saved FAA query manifests in `data/raw/faa/queries`
- raw FAA page snapshots in `data/raw/faa/pages`
- normalized `faa_signals` records in `data/processed/faa_signals`

Notes:

- use this for launch and space names where licensing, permits, or stakeholder pages move earlier than visible contract awards
- treat FAA pages as primary-source regulatory evidence, but keep the signal labeled by type such as license, permit, safety approval, or stakeholder page
- fetch the shared FAA page catalog once per run, then match it back to the requested companies and systems
