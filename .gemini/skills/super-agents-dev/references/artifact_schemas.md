# Super Agents Artifact Schemas

All artifacts are written to `dashboards/` as JSON.

## 1. Current Status (`<agent>_current_status.json`)
```json
{
  "agent_name": "biotech",
  "status": "running|completed|failed|idle",
  "workflow_name": "daily_scan",
  "task_name": "fetching_clinical_trials",
  "progress": { "completed": 5, "total": 10 },
  "active_source": "clinicaltrials.gov",
  "current_focus": "oncology pipeline",
  "latest_message": "Fetched 5 new trials"
}
```

## 2. Latest Run (`<agent>_run_latest.json`)
```json
{
  "run_id": "uuid",
  "agent_name": "biotech",
  "status": "completed",
  "started_at": "ISO-8601",
  "completed_at": "ISO-8601",
  "duration_seconds": 120,
  "outputs": {
    "records_written": 50,
    "files_written": 2
  },
  "findings": [
    {
      "severity": "high|medium|info",
      "finding_type": "new_trial",
      "asset": "Drug-X",
      "summary": "Phase III start confirmed",
      "source_url": "url",
      "confidence": "primary|secondary"
    }
  ],
  "next_actions": ["analyze_results"]
}
```

## 3. Findings (`<agent>_findings_latest.json`)
A flat array of finding objects (same schema as `findings` in Latest Run).

## 4. Risk Context (Inferred from `risk_badge.py`)
```json
{
  "overall_severity": "critical|high|medium|low|clear",
  "sanctions_hit": boolean,
  "conflict_nearby": boolean,
  "cyber_alert": boolean,
  "weather_hazard": boolean,
  "description": "Human readable detail"
}
```
