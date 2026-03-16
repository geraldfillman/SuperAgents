# Super Agents Implementation Plan

Updated: 2026-03-15

This plan focuses on the current multi-agent platform, not only the aerospace sector. The goal
is to make the existing sectors consistent, reviewable, and easy to extend before adding more
breadth.

## Phase 1: Docs Truth Pass

Status: completed on 2026-03-15

Target: make `docs/` match the live repository state.

Deliverables:

- repo-wide architecture doc
- repo-wide implementation plan
- current status snapshot that reflects the existing dashboard and runnable agents
- a small docs index that marks which files are canonical versus historical

Exit criteria:

- a new contributor can understand the platform without reverse-engineering the repo layout

## Phase 2: Dashboard Hardening

Status: in progress on 2026-03-15

Target: turn the existing Streamlit app into the real operations surface.

Deliverables:

- replace hardcoded agent lists with discovery from on-disk configs or CLI metadata
- support empty states for agents with no latest run or no findings yet
- standardize artifact paths and expected summary schemas
- document how dashboards consume run outputs

Completed in this pass:

- fleet overview, agent detail, run history, and findings pages now use shared dynamic agent
  discovery
- dashboard pages now share a central artifact-loading module instead of duplicating filesystem
  reads
- empty states now surface which runnable agents are missing status, findings, or run history
- the renewable-energy calendar now writes shared current-status and run-summary artifacts

Remaining exit criteria:

- adding a new runnable agent does not require hardcoded dashboard edits just to appear in the UI
- core sectors emit consistent artifact contracts so the dynamic UI has complete data to show

## Phase 3: Promote Biotech And Gaming To Package-Backed Agents

Status: initial scaffolding completed on 2026-03-15, deeper adoption still in progress

Target: stabilize the two agents that already have active dashboard artifacts and working scripts.

Deliverables:

- `src/super_agents/biotech/` with shared paths, watchlist, and I/O helpers
- `src/super_agents/gaming/` with the same pattern
- seed watchlists for both sectors
- script refactors away from ad hoc path handling
- tests for watchlist loaders and artifact-writing behavior

Completed in this pass:

- added starter biotech and gaming sector packages
- added biotech company and product watchlists plus a gaming studio watchlist
- refactored a first wave of scripts onto shared helpers
- restored direct script execution for the refactored scripts
- added watchlist tests

Remaining exit criteria:

- more scripts should migrate off duplicated local path logic where it still exists
- biotech and gaming should emit more consistent dashboard-ready artifact contracts

Exit criteria:

- biotech and gaming can scale without accumulating script-local duplication

## Phase 4: Cybersecurity Decision

Target: resolve whether cybersecurity is a near-term sector or a deferred placeholder.

If keeping it:

- add `.agent_cybersecurity/config.yaml`
- add workflow files
- land at least one runnable, high-signal script

If deferring it:

- label it as planned or archived in docs
- stop treating it as a current platform capability

Exit criteria:

- cybersecurity is either minimally real or explicitly deferred

## Phase 5: Graduate Fintech End To End

Status: initial scaffolding completed on 2026-03-15, live-source hardening still in progress

Target: build the second strong sector pattern after aerospace.

Why fintech first:

- runnable scripts already exist
- source access patterns are relatively straightforward
- it is a good fit for proving the reusable package plus workflow plus dashboard artifact model

Deliverables:

- `src/super_agents/fintech/`
- fintech seed watchlist
- one documented daily workflow
- one end-to-end smoke path with expected outputs checked into docs or examples

Completed in this pass:

- added a starter `src/super_agents/fintech/` package
- added a fintech seed watchlist
- added a documented daily workflow
- refactored fintech scripts onto shared helper modules
- wired the license tracker to shared current-status and run-summary artifacts

Remaining exit criteria:

- harden live-source access for the NMLS and OCC paths
- capture a successful end-to-end fintech smoke path instead of only failure-mode artifacts

Exit criteria:

- fintech reaches `READY` or at least strong `OPERATIONAL` status with repeatable artifacts

## Phase 6: Aerospace Live Ingestion

Target: deepen the strongest sector once the platform pattern is clearer.

Deliverables:

- live or manifest-backed `award_tracker`
- SEC procurement parsing connected to the aerospace watchlist
- SBIR and FAA signal ingestion wired into processed outputs
- watchlist ranking fed by live evidence rather than only seed structure

Exit criteria:

- aerospace becomes the strongest operational agent, not only the strongest code skeleton

## Phase 7: Repeat The Pattern Across Remaining Runnable Sectors

Target: extend the working pattern to `rare_earth`, `renewable_energy`, `quantum`, and
`autonomous_vehicles`.

Deliverables:

- sector package scaffolding where shared logic is growing
- seed watchlists
- documented workflows
- normalized dashboard artifacts

Exit criteria:

- each runnable sector follows the same operating contract, even if data depth differs

## Readiness Gates

Before promoting any sector to `READY`, confirm:

1. The agent is discoverable by the CLI.
2. At least one workflow runs end to end.
3. Seed data exists for the pilot universe.
4. The agent writes current-status and run-summary artifacts.
5. Findings preserve source and confidence metadata.
6. Shared logic has moved into `src/super_agents/<sector>/` when complexity warrants it.
7. Tests cover the core loaders and normalization behavior.

## Recommended Immediate Backlog

- standardize artifact writers for sectors that still do not emit dashboard-ready outputs
- decide whether cybersecurity should be built now
- harden fintech live sources next
- extend biotech and gaming helper adoption where it still removes duplication
- return to aerospace live ingestion after the reusable pattern is stable
