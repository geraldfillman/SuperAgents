"""
Score gaming titles on launch readiness and resilience.
"""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

OUT_DIR = Path("data/processed/title_scores")


@dataclass
class TitleScore:
    title_id: str
    title_name: str
    production_visibility: int
    funding_resilience: int
    launch_readiness: int
    storefront_momentum: int
    community_quality: int
    critic_upside: int
    portfolio_dependence: int
    post_launch_monetization: int
    execution_risk: int
    disclosure_quality: int
    notes: str = ""

    def composite_score(self) -> float:
        values = [
            self.production_visibility,
            self.funding_resilience,
            self.launch_readiness,
            self.storefront_momentum,
            self.community_quality,
            self.critic_upside,
            self.portfolio_dependence,
            self.post_launch_monetization,
            self.execution_risk,
            self.disclosure_quality,
        ]
        return round((sum(values) / len(values)) * 20.0, 1)

    def binary_launch_risk(self) -> str:
        if self.launch_readiness <= 2 or self.execution_risk >= 4 or self.portfolio_dependence >= 4:
            return "High"
        if self.launch_readiness == 3 or self.execution_risk == 3:
            return "Medium"
        return "Low"

    def dilution_risk(self) -> str:
        if self.funding_resilience <= 2:
            return "High"
        if self.funding_resilience == 3:
            return "Medium"
        return "Low"

    def release_confidence(self) -> str:
        if min(self.production_visibility, self.launch_readiness, self.disclosure_quality) >= 4:
            return "High"
        if min(self.production_visibility, self.launch_readiness) >= 3:
            return "Medium"
        return "Low"

    def to_record(self) -> dict:
        now = datetime.now(timezone.utc)
        record = asdict(self)
        record.update(
            {
                "score_id": f"{self.title_id}_{now.strftime('%Y%m%d_%H%M%S')}",
                "composite_score": self.composite_score(),
                "binary_launch_risk": self.binary_launch_risk(),
                "dilution_risk": self.dilution_risk(),
                "release_confidence": self.release_confidence(),
                "scored_by": "system",
                "scored_at": now.isoformat(),
            }
        )
        return record


def _sample_batch() -> list[dict]:
    return [
        {
            "title_id": "TITLE_ALPHA",
            "title_name": "Title Alpha",
            "production_visibility": 4,
            "funding_resilience": 3,
            "launch_readiness": 4,
            "storefront_momentum": 3,
            "community_quality": 3,
            "critic_upside": 4,
            "portfolio_dependence": 4,
            "post_launch_monetization": 3,
            "execution_risk": 2,
            "disclosure_quality": 4,
            "notes": "Sample scoring seed",
        },
        {
            "title_id": "TITLE_BETA",
            "title_name": "Title Beta",
            "production_visibility": 2,
            "funding_resilience": 2,
            "launch_readiness": 2,
            "storefront_momentum": 3,
            "community_quality": 2,
            "critic_upside": 3,
            "portfolio_dependence": 5,
            "post_launch_monetization": 2,
            "execution_risk": 4,
            "disclosure_quality": 2,
            "notes": "Sample risk-heavy title",
        },
    ]


def _load_inputs(input_json: Path | None, batch: bool) -> list[dict]:
    if input_json is not None:
        payload = json.loads(input_json.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return [payload]
        return []
    if batch:
        return _sample_batch()
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Score gaming titles")
    parser.add_argument("--title-id", type=str, help="Single title identifier for reporting only")
    parser.add_argument("--input-json", type=Path, help="Input JSON object or array")
    parser.add_argument("--batch", action="store_true", help="Run a sample batch if no input file is provided")
    parser.add_argument("--active-only", action="store_true", help="Accepted for workflow compatibility")
    args = parser.parse_args()

    inputs = _load_inputs(args.input_json, args.batch)
    if not inputs:
        print("No scoring payload provided. Use --input-json or --batch.")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = [TitleScore(**payload).to_record() for payload in inputs]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"title_scores_{timestamp}.json"
    out_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Saved {len(records)} title scores to {out_path}")
    if args.title_id:
        matching = [record for record in records if record["title_id"] == args.title_id]
        if matching:
            print(json.dumps(matching[0], indent=2))


if __name__ == "__main__":
    main()
