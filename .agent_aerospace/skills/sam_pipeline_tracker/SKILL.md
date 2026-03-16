# SAM Pipeline Tracker

Purpose: track pre-award demand for small-cap and microcap names using official SAM.gov opportunities data.

Inputs:

- tracked companies and systems
- optional ticker or manual company name
- optional agency filter note
- live fetch mode requires a `SAM_API_KEY`

Outputs:

- saved SAM query manifests in `data/raw/sam/queries`
- raw SAM opportunity payloads in `data/raw/sam/opportunities`
- normalized `pipeline_signals` records in `data/processed/pipeline_signals`

Notes:

- default behavior should be query-manifest generation because the public opportunities API requires an API key
- system names and system-type phrases are usually better microcap queries than ticker symbols alone
