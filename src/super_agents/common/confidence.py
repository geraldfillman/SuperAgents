"""Source confidence tagging per project.md section 7.

Every record written by any agent must carry:
- source_url
- source_type
- source_confidence

This module provides the canonical types and a builder/validator so
agents don't scatter raw strings across their output.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class SourceConfidence(str, Enum):
    """Confidence level for a data source.

    Values match project.md section 7 exactly.
    """

    PRIMARY = "primary"
    """Official registry, database, store page, or filing."""

    SECONDARY = "secondary"
    """SEC filing interpretation, third-party structured data, aggregator."""

    SPONSOR = "sponsor"
    """Company press release, investor presentation, self-reported milestone."""

    def __str__(self) -> str:
        return self.value


class SourceType(str, Enum):
    """Common source types across all agents."""

    API = "api"
    SCRAPE = "scrape"
    FILING = "filing"
    DATABASE = "database"
    PRESS_RELEASE = "press_release"
    MANUAL = "manual"

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------

REQUIRED_SOURCE_FIELDS = frozenset({"source_url", "source_type", "source_confidence"})


def tag_source(
    record: dict[str, Any],
    *,
    source_url: str,
    source_type: str | SourceType,
    source_confidence: str | SourceConfidence,
) -> dict[str, Any]:
    """Return a new record with source provenance fields added.

    Immutable — does not mutate the original dict.

    Args:
        record: The data record to tag.
        source_url: URL where the data was obtained.
        source_type: How the data was obtained (api, scrape, filing, etc.).
        source_confidence: Trust level (primary, secondary, sponsor).

    Returns:
        A new dict with the source fields merged in.

    Raises:
        ValueError: If source_confidence is not a valid level.
    """
    confidence = _normalize_confidence(source_confidence)
    source_type_str = str(source_type)

    return {
        **record,
        "source_url": source_url,
        "source_type": source_type_str,
        "source_confidence": str(confidence),
    }


def validate_source_fields(record: dict[str, Any]) -> list[str]:
    """Check a record for missing or invalid source provenance fields.

    Returns:
        List of issue strings. Empty list means the record is valid.
    """
    issues: list[str] = []

    for field in REQUIRED_SOURCE_FIELDS:
        value = record.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            issues.append(f"missing_{field}")

    confidence_raw = record.get("source_confidence", "")
    if confidence_raw:
        valid_values = {e.value for e in SourceConfidence}
        if confidence_raw not in valid_values:
            issues.append(
                f"invalid_source_confidence: '{confidence_raw}' "
                f"(expected one of: {', '.join(sorted(valid_values))})"
            )

    return issues


def is_sponsor_only(record: dict[str, Any]) -> bool:
    """Check if a record relies solely on sponsor-provided data."""
    return record.get("source_confidence") == SourceConfidence.SPONSOR.value


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _normalize_confidence(value: str | SourceConfidence) -> SourceConfidence:
    """Convert a string to SourceConfidence, raising on invalid input."""
    if isinstance(value, SourceConfidence):
        return value
    try:
        return SourceConfidence(value.lower().strip())
    except ValueError:
        valid = ", ".join(e.value for e in SourceConfidence)
        raise ValueError(
            f"Invalid source_confidence: '{value}'. Must be one of: {valid}"
        )
