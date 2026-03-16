"""SEC procurement signal extraction helpers."""

from __future__ import annotations

import re
from pathlib import Path

from .io_utils import write_json
from .paths import ensure_directory, project_path

SIGNAL_DEFINITIONS = {
    "ota": {
        "patterns": [r"\bOTA\b", r"other transaction authority"],
        "milestone_type": "prototype_vehicle",
        "priority": "high",
    },
    "idiq": {
        "patterns": [r"\bIDIQ\b", r"indefinite delivery(?:\/indefinite quantity)?"],
        "milestone_type": "contract_vehicle",
        "priority": "high",
    },
    "sbir": {
        "patterns": [r"\bSBIR\b", r"\bSTTR\b", r"phase (?:i|ii|iii) sbir"],
        "milestone_type": "innovation_funding",
        "priority": "medium",
    },
    "downselect": {
        "patterns": [r"downselect", r"selected for the next phase", r"advanced to the next phase"],
        "milestone_type": "competitive_selection",
        "priority": "high",
    },
    "production": {
        "patterns": [
            r"low-rate initial production",
            r"full-rate production",
            r"production lot",
            r"lot \d+ production",
        ],
        "milestone_type": "production",
        "priority": "high",
    },
    "protest": {
        "patterns": [r"bid protest", r"award protest", r"gao protest"],
        "milestone_type": "procurement_risk",
        "priority": "high",
    },
    "option_exercise": {
        "patterns": [r"option exercise", r"exercised the option", r"exercise of an option"],
        "milestone_type": "contract_extension",
        "priority": "medium",
    },
    "launch_manifest": {
        "patterns": [r"launch manifest", r"scheduled for launch", r"launch campaign"],
        "milestone_type": "launch_window",
        "priority": "medium",
    },
}

DEFAULT_SIGNAL_DIR = project_path("data", "processed", "sec_signals")


def extract_procurement_signals(
    text: str,
    *,
    metadata: dict | None = None,
    context_chars: int = 120,
) -> list[dict]:
    """Extract procurement signals from filing text."""
    meta = metadata or {}
    results: list[dict] = []
    seen_keys: set[tuple[str, int, int]] = set()

    for signal_type, definition in SIGNAL_DEFINITIONS.items():
        for pattern in definition["patterns"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                key = (signal_type, match.start(), match.end())
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                start = max(0, match.start() - context_chars)
                end = min(len(text), match.end() + context_chars)
                results.append(
                    {
                        "signal_type": signal_type,
                        "milestone_type": definition["milestone_type"],
                        "priority": definition["priority"],
                        "matched_text": match.group(0),
                        "context": text[start:end].strip(),
                        "company_name": meta.get("company_name", ""),
                        "ticker": meta.get("ticker", ""),
                        "cik": meta.get("cik", ""),
                        "form_type": meta.get("form_type", ""),
                        "filing_date": meta.get("filing_date", ""),
                        "source_url": meta.get("source_url", ""),
                        "source_type": meta.get("source_type", "SEC"),
                        "source_confidence": meta.get("source_confidence", "secondary"),
                    }
                )

    results.sort(key=lambda item: (item["signal_type"], item["matched_text"].lower()))
    return results


def read_filing_text(path: Path) -> str:
    """Read filing text with permissive decoding."""
    return path.read_text(encoding="utf-8", errors="ignore")


def write_signal_file(input_path: Path, signals: list[dict], output_dir: Path | None = None) -> Path:
    """Persist extracted signals and return the output path."""
    destination = ensure_directory(output_dir or DEFAULT_SIGNAL_DIR)
    out_path = destination / f"{input_path.stem}_signals.json"
    write_json(out_path, signals)
    return out_path
