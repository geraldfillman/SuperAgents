# SBIR Tracker

Purpose: surface early-stage non-dilutive traction for small-cap and microcap names through official SBIR award data.

Inputs:

- tracked watchlist companies
- optional ticker or manual company name
- optional agency and year filters

Outputs:

- raw SBIR award API payloads in `data/raw/sbir/awards`
- normalized `sbir_awards` records in `data/processed/sbir_awards`

Notes:

- use this before trailing contract-award feeds when a company is too early-stage for large visible defense awards
- normalized records should be matched back to the tracked watchlist, not accepted blindly from broad firm-name search results
- the public API can rate-limit; query manifests should still be saved so retries do not lose scope
