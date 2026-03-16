"""Capture analyst-provided TRL evidence and write normalized records."""

from __future__ import annotations

import argparse

from adt_agent.trl import build_trl_signal, persist_trl_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a TRL signal")
    parser.add_argument("--system", required=True, help="System or platform name")
    parser.add_argument("--trl", required=True, type=int, help="TRL level 1-9")
    parser.add_argument("--evidence", required=True, help="Observed milestone or evidence")
    parser.add_argument("--company", help="Company name")
    parser.add_argument("--ticker", help="Ticker")
    parser.add_argument("--milestone-type", default="test_event", help="Milestone type label")
    parser.add_argument("--event-date", help="Observed event date in ISO format")
    parser.add_argument("--expected-date", help="Future milestone date in ISO format")
    parser.add_argument("--status", default="observed", help="Observed status")
    parser.add_argument("--source-url", help="Optional source URL")
    parser.add_argument("--source-type", default="manual", help="Source system label")
    parser.add_argument("--source-confidence", default="manual", help="Confidence label")
    args = parser.parse_args()

    signal = build_trl_signal(
        system_name=args.system,
        trl_level=args.trl,
        evidence_summary=args.evidence,
        company_name=args.company or "",
        ticker=args.ticker or "",
        milestone_type=args.milestone_type,
        event_date=args.event_date,
        expected_date=args.expected_date or "",
        source_url=args.source_url or "",
        source_type=args.source_type,
        source_confidence=args.source_confidence,
        status=args.status,
    )
    written_paths = persist_trl_bundle(signal)
    print(f"Wrote {len(written_paths)} TRL-related record(s)")
    for path in written_paths:
        print(path)


if __name__ == "__main__":
    main()
