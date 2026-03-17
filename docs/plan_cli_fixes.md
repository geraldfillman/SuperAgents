# Plan: CLI Fixes

**Status:** Draft
**Date:** 2026-03-17
**Scope:** Fix all broken CLI commands so every `python -m super_agents <command>` works

---

## Current State (Audit Results)

### Commands That Work
| Command | Status | Notes |
|---------|--------|-------|
| `list` | OK | Discovers all agents, shows skills/scripts |
| `crucix status` | OK | Shows integration status |
| `crucix signals` | OK | Queries signal store (empty but functional) |
| `crucix sources` | OK | Lists source mappings |
| `simulate` | OK | Runs scenarios with rules engine |

### Commands That Fail
| Command | Error | Root Cause |
|---------|-------|------------|
| `run --agent aerospace ...` | `ModuleNotFoundError: adt_agent` | All 14 aerospace scripts import from `adt_agent` but module lives at `super_agents.aerospace` |
| `run --agent biotech --skill fda_tracker ...` | `httpx.HTTPStatusError: 500` | FDA API returns 500 — no retry/graceful error handling |
| `search --agent biotech` (fetch_trials) | `unrecognized arguments: --status` | Search config passes `--status RECRUITING` but script accepts `--condition`, `--phase`, `--sponsor`, `--nct`, `--limit` only |
| `run --agent renewable_energy ...` (extract_energy_catalysts) | `NameError: 'argparse' not defined` | Script uses `argparse.ArgumentParser` but never imports `argparse` |
| `orchestrate *` | `tmux is not installed` | tmux unavailable on Windows — no fallback |
| `crucix sweep` | Hangs/blocks | Tries to run Crucix sidecar which may not be running |

### Agents With No Scripts (Empty — Not Broken)
| Agent | Reason |
|-------|--------|
| `cannabis_psychedelics` | No scripts directory populated yet |
| `meddevice` | No scripts directory populated yet |
| `space` | No scripts directory populated yet |

---

## Fix Plan

### Phase 1: Critical Import Fixes (14 aerospace scripts)

**Problem:** All `.agent_aerospace/skills/*/scripts/*.py` files import from `adt_agent.*` — the old module name from before the monorepo migration. The actual code lives at `src/super_agents/aerospace/`.

**Fix:** Rewrite imports in all 14 scripts: `from adt_agent.X import ...` → `from super_agents.aerospace.X import ...`

**Files (all under `.agent_aerospace/skills/`):**
1. `award_tracker/scripts/fetch_awards.py` — `adt_agent.awards`
2. `budget_tracker/scripts/fetch_budget_lines.py` — `adt_agent.budgets`
3. `budget_tracker/scripts/reconcile_budget_exposure.py` — `adt_agent.scorecards`
4. `faa_license_tracker/scripts/fetch_faa_signals.py` — `adt_agent.faa`
5. `financial_monitor/scripts/fetch_financials.py` — `adt_agent.financials`
6. `insider_tracker/scripts/monitor_form4.py` — `adt_agent.insiders`
7. `program_calendar/scripts/build_program_calendar.py` — `adt_agent.calendar`
8. `results_dashboard/scripts/build_results_dashboard.py` — `adt_agent.dashboard`
9. `sam_pipeline_tracker/scripts/fetch_sam_pipeline.py` — `adt_agent.sam`
10. `sbir_tracker/scripts/fetch_sbir_awards.py` — `adt_agent.sbir`
11. `sec_procurement_parser/scripts/extract_procurement_signals.py` — `adt_agent.io_utils`
12. `sec_procurement_parser/scripts/fetch_sec_filings.py` — `adt_agent.sec`
13. `trl_tracker/scripts/track_trl_signals.py` — `adt_agent.trl`
14. `watchlist_ranker/scripts/build_watchlist_ranking.py` — `adt_agent.ranking`

**Verification:** After fix, `python <script> --help` must exit 0 for all 14.

---

### Phase 2: Search Config Mismatches

**Problem:** `_build_search_configs()` in `cli.py` passes arguments that don't match actual script signatures.

**Fix in `cli.py` line 33:**
```python
# BEFORE (broken)
("clinicaltrials_scraper", "fetch_trials", ["--status", "RECRUITING", "--limit", "5"]),

# AFTER (matches actual script args)
("clinicaltrials_scraper", "fetch_trials", ["--condition", "cancer", "--limit", "5"]),
```

**Verification:** `python -m super_agents search --agent biotech` must not show `unrecognized arguments`.

---

### Phase 3: Missing Import Fix (renewable_energy)

**Problem:** `.agent_renewable_energy/skills/sec_filings_parser/scripts/extract_energy_catalysts.py` uses `argparse.ArgumentParser()` at line 256 but never imports `argparse`.

**Fix:** Add `import argparse` to the import block at the top of the file.

**Verification:** `python <script> --help` exits 0.

---

### Phase 4: Error Handling for External APIs

**Problem:** Scripts like `fetch_drug_approvals.py` call `response.raise_for_status()` with no retry or graceful degradation. FDA API returns 500 — the script crashes.

**Fix:** Add retry logic with exponential backoff and graceful error messages to scripts that hit external APIs. Use `httpx` retry or a simple wrapper:

```python
def _fetch_with_retry(client, url, params, max_retries=3):
    for attempt in range(max_retries):
        response = client.get(url, params=params)
        if response.status_code == 500 and attempt < max_retries - 1:
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        return response
    raise RuntimeError(f"API returned 500 after {max_retries} retries: {url}")
```

**Scope:** Biotech scripts that hit FDA API, ClinicalTrials.gov, SEC EDGAR.

---

### Phase 5: Orchestrator Windows Compatibility

**Problem:** `orchestrate` command requires tmux, which doesn't exist on Windows. The error message says "install with apt-get" which is Linux-only advice.

**Options (pick one):**
1. **Subprocess fallback:** Replace tmux sessions with background `subprocess.Popen` processes + log files on Windows
2. **WSL bridge:** Detect WSL and delegate tmux ops there
3. **Graceful skip:** Better error message: "orchestrate requires tmux (Linux/macOS/WSL). On Windows, use WSL or run individual scripts with `run`."

**Recommended:** Option 3 short-term (fix error message), Option 1 for full Windows support later.

---

### Phase 6: Crucix Sweep Reliability

**Problem:** `crucix sweep` can hang if the Crucix sidecar isn't running.

**Fix:** Add a timeout and pre-check: ping the sidecar before attempting a sweep. If sidecar is down, print actionable error.

---

## Priority Order

| Priority | Phase | Effort | Impact |
|----------|-------|--------|--------|
| P0 | Phase 1 — Aerospace imports | ~30 min | Unblocks 14 scripts (entire agent) |
| P0 | Phase 2 — Search config | ~5 min | Fixes `search` command |
| P0 | Phase 3 — Missing argparse import | ~2 min | Fixes 1 script |
| P1 | Phase 4 — API error handling | ~1 hr | Resilience for all external API scripts |
| P1 | Phase 5 — Windows orchestrator | ~2 hr (Option 1) or 5 min (Option 3) | Enables orchestrate on Windows |
| P2 | Phase 6 — Crucix sweep | ~30 min | Prevents hangs |

---

## Success Criteria

After all fixes:
```bash
python -m super_agents list                    # All agents display
python -m super_agents search --agent biotech  # All 3 searches succeed or degrade gracefully
python -m super_agents search --agent aerospace # award_tracker search succeeds
python -m super_agents run --agent aerospace --skill award_tracker --script fetch_awards -- --days 30  # Runs without import error
python -m super_agents orchestrate status      # Shows useful message on Windows
python -m super_agents simulate scenarios/hormuz_zero_transit.yaml --summary  # Already works
python -m super_agents crucix status           # Already works
```
