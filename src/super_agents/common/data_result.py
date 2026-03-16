"""Standard data contracts for the Super_Agents pipeline.

Three roles:
  1. Data Hub (Crucix) emits **Signal** objects when something changes.
  2. Agent skills consume signals and produce **DataResult** objects.
  3. The Simulation Engine consumes DataResults as scenario inputs.

Using frozen dataclasses enforces immutability — records flow through
the pipeline without hidden mutation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# RunMetadata — timing and provenance for every skill execution
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunMetadata:
    """Metadata attached to every skill run."""

    agent: str
    skill: str
    run_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    source_urls: tuple[str, ...] = ()
    error: str | None = None

    def complete(self) -> RunMetadata:
        """Return a new RunMetadata marked as completed with duration calculated."""
        now = datetime.now()
        duration = (now - self.started_at).total_seconds()
        return RunMetadata(
            agent=self.agent,
            skill=self.skill,
            run_id=self.run_id,
            started_at=self.started_at,
            completed_at=now,
            duration_seconds=round(duration, 2),
            source_urls=self.source_urls,
            error=self.error,
        )

    def with_error(self, error: str) -> RunMetadata:
        """Return a new RunMetadata with an error message attached."""
        return RunMetadata(
            agent=self.agent,
            skill=self.skill,
            run_id=self.run_id,
            started_at=self.started_at,
            completed_at=self.completed_at,
            duration_seconds=self.duration_seconds,
            source_urls=self.source_urls,
            error=error,
        )


# ---------------------------------------------------------------------------
# DataResult — what every agent skill produces
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DataResult:
    """Standard output from any agent skill execution.

    Attributes:
        agent: Agent name (e.g. 'biotech', 'gaming').
        skill: Skill name (e.g. 'fda_tracker', 'storefront_monitor').
        run_id: Unique run identifier.
        records: The actual data records produced.
        metadata: Timing and provenance information.
        findings: High-level findings for the dashboard.
        record_count: Number of records produced.
    """

    agent: str
    skill: str
    run_id: str
    records: tuple[dict[str, Any], ...] = ()
    metadata: RunMetadata | None = None
    findings: tuple[dict[str, Any], ...] = ()
    record_count: int = 0

    @classmethod
    def from_records(
        cls,
        agent: str,
        skill: str,
        records: list[dict[str, Any]],
        metadata: RunMetadata | None = None,
        findings: list[dict[str, Any]] | None = None,
    ) -> DataResult:
        """Convenience factory from a list of dicts.

        Converts mutable lists to tuples for immutability.
        """
        record_tuple = tuple(records)
        finding_tuple = tuple(findings) if findings else ()
        return cls(
            agent=agent,
            skill=skill,
            run_id=metadata.run_id if metadata else datetime.now().strftime("%Y%m%d_%H%M%S"),
            records=record_tuple,
            metadata=metadata,
            findings=finding_tuple,
            record_count=len(record_tuple),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "agent": self.agent,
            "skill": self.skill,
            "run_id": self.run_id,
            "record_count": self.record_count,
            "records": list(self.records),
            "findings": list(self.findings),
            "metadata": {
                "agent": self.metadata.agent,
                "skill": self.metadata.skill,
                "run_id": self.metadata.run_id,
                "started_at": self.metadata.started_at.isoformat(),
                "completed_at": self.metadata.completed_at.isoformat() if self.metadata.completed_at else None,
                "duration_seconds": self.metadata.duration_seconds,
                "source_urls": list(self.metadata.source_urls),
                "error": self.metadata.error,
            } if self.metadata else None,
        }


# ---------------------------------------------------------------------------
# Signal — what the data hub (Crucix) emits when something changes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Signal:
    """An event from the data hub indicating something changed.

    Signals flow from Crucix (or any data source) into the agent router,
    which decides which agents should react.

    Attributes:
        source: Origin system (e.g. 'crucix', 'manual', 'scheduled').
        topic: What changed (e.g. 'oil_price_spike', 'fda_approval', 'strait_closure').
        payload: Structured data about the change.
        timestamp: When the signal was created.
        signal_id: Unique identifier for deduplication.
        confidence: How reliable is this signal.
        sectors: Which agent sectors should care about this signal.
    """

    source: str
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    confidence: str = "secondary"
    sectors: tuple[str, ...] = ()

    def matches_sector(self, sector: str) -> bool:
        """Check if this signal is relevant to a given sector."""
        if not self.sectors:
            return True  # empty means broadcast to all
        return sector in self.sectors

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "signal_id": self.signal_id,
            "source": self.source,
            "topic": self.topic,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "sectors": list(self.sectors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Signal:
        """Deserialize from a dictionary."""
        return cls(
            source=data["source"],
            topic=data["topic"],
            payload=data.get("payload", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            signal_id=data.get("signal_id", str(uuid.uuid4())),
            confidence=data.get("confidence", "secondary"),
            sectors=tuple(data.get("sectors", ())),
        )
