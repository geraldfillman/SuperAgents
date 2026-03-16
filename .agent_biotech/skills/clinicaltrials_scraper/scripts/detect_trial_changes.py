"""
ClinicalTrials Scraper — Detect Trial Changes
Compares current ClinicalTrials.gov data against stored snapshots to detect updates.
"""

import json
from datetime import datetime
from pathlib import Path

SNAPSHOTS_DIR = Path("data/snapshots/clinicaltrials")
PROCESSED_DIR = Path("data/processed/clinicaltrials")

# Fields to monitor for changes
WATCHED_FIELDS = [
    "status",
    "phase",
    "estimated_primary_completion",
    "estimated_study_completion",
    "results_posted",
]


def detect_changes(current_trials: list[dict]) -> dict:
    """
    Compare current trial data against the most recent snapshot.

    Returns:
        {
            "new_trials": [...],
            "changed_trials": [{"nct_id": ..., "changes": {...}}],
            "unchanged_count": int,
            "snapshot_date": str,
        }
    """
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Load most recent snapshot
    previous = _load_latest_snapshot()
    previous_by_nct = {t["nct_id"]: t for t in previous}

    new_trials = []
    changed_trials = []
    unchanged_count = 0

    for trial in current_trials:
        nct_id = trial.get("nct_id", "")
        if not nct_id:
            continue

        if nct_id not in previous_by_nct:
            new_trials.append(trial)
            continue

        old = previous_by_nct[nct_id]
        changes = {}
        for field in WATCHED_FIELDS:
            old_val = old.get(field)
            new_val = trial.get(field)
            if old_val != new_val:
                changes[field] = {"old": old_val, "new": new_val}

        if changes:
            changed_trials.append({
                "nct_id": nct_id,
                "title": trial.get("title", ""),
                "sponsor": trial.get("sponsor", ""),
                "changes": changes,
            })
        else:
            unchanged_count += 1

    # Save current as new snapshot
    _save_snapshot(current_trials)

    # Save change report
    report = {
        "detected_at": datetime.now().isoformat(),
        "new_trials": new_trials,
        "changed_trials": changed_trials,
        "unchanged_count": unchanged_count,
    }
    report_path = PROCESSED_DIR / f"changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))

    return report


def _load_latest_snapshot() -> list[dict]:
    """Load the most recent snapshot file."""
    if not SNAPSHOTS_DIR.exists():
        return []

    snapshots = sorted(SNAPSHOTS_DIR.glob("snapshot_*.json"))
    if not snapshots:
        return []

    return json.loads(snapshots[-1].read_text())


def _save_snapshot(trials: list[dict]) -> Path:
    """Save current trial data as a timestamped snapshot."""
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOTS_DIR / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(trials, indent=2, default=str))
    return path


if __name__ == "__main__":
    # Example: detect changes from last snapshot (requires prior fetch)
    from fetch_trials import search_trials

    current = search_trials(sponsor="Moderna")
    report = detect_changes(current)
    print(f"New trials: {len(report['new_trials'])}")
    print(f"Changed trials: {len(report['changed_trials'])}")
    print(f"Unchanged: {report['unchanged_count']}")
    for change in report["changed_trials"][:5]:
        print(f"  {change['nct_id']}: {change['changes']}")
