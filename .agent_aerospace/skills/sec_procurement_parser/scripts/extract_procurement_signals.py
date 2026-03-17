"""Extract procurement language from local filing text."""

from __future__ import annotations

import argparse
from pathlib import Path

from super_agents.aerospace.io_utils import read_json
from super_agents.aerospace.procurement import extract_procurement_signals, read_filing_text, write_signal_file
from super_agents.aerospace.sec import find_latest_filing_manifest


def _load_manifest_metadata(manifest_path: Path | None) -> dict[str, dict]:
    if manifest_path is None or not manifest_path.exists():
        return {}

    manifest = read_json(manifest_path)
    metadata_by_name: dict[str, dict] = {}
    for filing in manifest.get("filings", []):
        text_path = filing.get("text_path", "")
        if not text_path:
            continue
        metadata_by_name[Path(text_path).name] = {
            "company_name": filing.get("company_name", manifest.get("company_name", "")),
            "ticker": filing.get("ticker", manifest.get("ticker", "")),
            "cik": filing.get("cik", manifest.get("cik", "")),
            "form_type": filing.get("form_type", ""),
            "filing_date": filing.get("filing_date", ""),
            "source_url": filing.get("filing_url", ""),
        }
    return metadata_by_name


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract procurement keywords from local filing text")
    parser.add_argument("--input", type=Path, help="Path to a local text file")
    parser.add_argument("--input-dir", type=Path, help="Directory of local text files")
    parser.add_argument("--manifest", type=Path, help="Optional filing manifest for metadata enrichment")
    parser.add_argument("--company", help="Company name")
    parser.add_argument("--ticker", help="Ticker")
    parser.add_argument("--cik", help="CIK")
    parser.add_argument("--form-type", help="Form type, for example 8-K")
    parser.add_argument("--filing-date", help="Filing date in ISO format")
    parser.add_argument("--source-url", help="Original filing URL")
    parser.add_argument("--output-dir", type=Path, help="Override output directory")
    args = parser.parse_args()

    if bool(args.input) == bool(args.input_dir):
        raise SystemExit("Provide exactly one of --input or --input-dir.")

    input_paths = [args.input] if args.input else sorted(args.input_dir.glob("*.txt"))
    if not input_paths:
        raise SystemExit("No input text files were found.")

    manifest_path = args.manifest
    if manifest_path is None and args.ticker:
        manifest_path = find_latest_filing_manifest(args.ticker)
    metadata_by_name = _load_manifest_metadata(manifest_path)

    total_signals = 0
    for input_path in input_paths:
        text = read_filing_text(input_path)
        base_metadata = metadata_by_name.get(input_path.name, {})
        signals = extract_procurement_signals(
            text,
            metadata={
                "company_name": args.company or base_metadata.get("company_name", ""),
                "ticker": args.ticker or base_metadata.get("ticker", ""),
                "cik": args.cik or base_metadata.get("cik", ""),
                "form_type": args.form_type or base_metadata.get("form_type", ""),
                "filing_date": args.filing_date or base_metadata.get("filing_date", ""),
                "source_url": args.source_url or base_metadata.get("source_url", ""),
            },
        )
        out_path = write_signal_file(input_path, signals, output_dir=args.output_dir)
        total_signals += len(signals)
        print(f"{input_path.name}: {len(signals)} signals -> {out_path}")

    print(f"Extracted {total_signals} signals across {len(input_paths)} file(s)")


if __name__ == "__main__":
    main()
