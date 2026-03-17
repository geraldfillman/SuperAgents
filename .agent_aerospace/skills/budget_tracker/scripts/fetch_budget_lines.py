"""Fetch or parse official budget PDFs into normalized budget-line records."""

from __future__ import annotations

import argparse
from pathlib import Path

from super_agents.aerospace.budgets import download_budget_pdf, parse_budget_pdf, save_budget_lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest official DoD budget PDFs into budget_lines records")
    parser.add_argument("--url", help="Official PDF URL")
    parser.add_argument("--pdf", type=Path, help="Local PDF path")
    parser.add_argument("--kind", choices=("p1", "rdte"), help="Budget document family")
    parser.add_argument("--agency", help="Override inferred agency label")
    parser.add_argument("--fiscal-year", type=int, help="Override inferred fiscal year")
    parser.add_argument("--status", default="requested", help="Budget-line status label")
    parser.add_argument("--label", help="Output label override")
    args = parser.parse_args()

    if bool(args.url) == bool(args.pdf):
        raise SystemExit("Provide exactly one of --url or --pdf.")

    pdf_path = download_budget_pdf(args.url, label=args.label) if args.url else args.pdf
    if pdf_path is None or not pdf_path.exists():
        raise SystemExit("The requested PDF could not be found.")

    resolved_kind, records, text_path = parse_budget_pdf(
        pdf_path,
        kind=args.kind,
        agency=args.agency,
        fiscal_year=args.fiscal_year,
        status=args.status,
        source_url=args.url or str(pdf_path),
        label=args.label,
    )
    out_path = save_budget_lines(records, label=args.label or pdf_path.stem)

    print(f"Parsed {len(records)} budget line(s) from {resolved_kind}")
    print(pdf_path)
    print(text_path)
    print(out_path)


if __name__ == "__main__":
    main()
