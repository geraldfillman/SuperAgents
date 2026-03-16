"""
Product Scoring — Score products on 10 dimensions + compute derived flags.
Based on the scoring model defined in Biotech.md.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

PROCESSED_DIR = Path("data/processed/scores")


@dataclass
class ProductScore:
    """Score a biotech product on 10 dimensions (1-5 scale)."""

    product_id: str = ""
    product_name: str = ""

    # Primary scoring dimensions (1-5)
    evidence_maturity: int = 0
    endpoint_clarity: int = 0
    trial_design_quality: int = 0
    regulatory_advantage: int = 0
    unmet_need_severity: int = 0
    mechanism_plausibility: int = 0
    manufacturing_complexity_risk: int = 0
    safety_uncertainty: int = 0
    sponsor_disclosure_quality: int = 0
    near_term_catalyst_density: int = 0

    # Derived flags (computed)
    binary_event_risk: str = ""
    regulatory_visibility: str = ""
    science_readthrough_value: str = ""
    crowded_indication_penalty: str = ""
    approval_path_complexity: str = ""

    # Metadata
    scored_by: str = ""
    scored_at: str = ""
    notes: str = ""

    @property
    def composite_score(self) -> float:
        """Weighted composite score (0-100)."""
        dims = [
            self.evidence_maturity,
            self.endpoint_clarity,
            self.trial_design_quality,
            self.regulatory_advantage,
            self.unmet_need_severity,
            self.mechanism_plausibility,
            self.manufacturing_complexity_risk,
            self.safety_uncertainty,
            self.sponsor_disclosure_quality,
            self.near_term_catalyst_density,
        ]
        if not any(dims):
            return 0.0
        return (sum(dims) / (len(dims) * 5)) * 100

    def compute_derived_flags(
        self,
        num_competitors_in_indication: int = 0,
        has_official_fda_date: bool = False,
        is_single_catalyst_company: bool = False,
        is_first_in_class: bool = False,
        has_multi_indication_potential: bool = False,
    ) -> None:
        """Compute derived risk flags based on scoring + external context."""

        # Binary event risk
        if is_single_catalyst_company and self.near_term_catalyst_density >= 4:
            self.binary_event_risk = "High"
        elif self.near_term_catalyst_density >= 3:
            self.binary_event_risk = "Medium"
        else:
            self.binary_event_risk = "Low"

        # Regulatory visibility
        if has_official_fda_date:
            self.regulatory_visibility = "High"
        elif self.regulatory_advantage >= 3:
            self.regulatory_visibility = "Medium"
        else:
            self.regulatory_visibility = "Low"

        # Science readthrough value
        if has_multi_indication_potential and self.mechanism_plausibility >= 4:
            self.science_readthrough_value = "High"
        elif self.mechanism_plausibility >= 3:
            self.science_readthrough_value = "Medium"
        else:
            self.science_readthrough_value = "Low"

        # Crowded indication penalty
        if num_competitors_in_indication > 5:
            self.crowded_indication_penalty = "High"
        elif num_competitors_in_indication > 2:
            self.crowded_indication_penalty = "Medium"
        else:
            self.crowded_indication_penalty = "Low"

        # Approval path complexity
        if is_first_in_class or self.endpoint_clarity <= 2:
            self.approval_path_complexity = "High"
        elif self.trial_design_quality <= 3:
            self.approval_path_complexity = "Medium"
        else:
            self.approval_path_complexity = "Low"


def score_product(product_data: dict, context: dict | None = None) -> dict:
    """
    Score a product and return the full assessment.

    Args:
        product_data: Dict with scoring dimensions (1-5 values)
        context: Optional context for derived flags
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    from datetime import datetime

    score = ProductScore(
        product_id=product_data.get("product_id", ""),
        product_name=product_data.get("product_name", ""),
        evidence_maturity=product_data.get("evidence_maturity", 0),
        endpoint_clarity=product_data.get("endpoint_clarity", 0),
        trial_design_quality=product_data.get("trial_design_quality", 0),
        regulatory_advantage=product_data.get("regulatory_advantage", 0),
        unmet_need_severity=product_data.get("unmet_need_severity", 0),
        mechanism_plausibility=product_data.get("mechanism_plausibility", 0),
        manufacturing_complexity_risk=product_data.get("manufacturing_complexity_risk", 0),
        safety_uncertainty=product_data.get("safety_uncertainty", 0),
        sponsor_disclosure_quality=product_data.get("sponsor_disclosure_quality", 0),
        near_term_catalyst_density=product_data.get("near_term_catalyst_density", 0),
        scored_by=product_data.get("scored_by", "agent"),
        scored_at=datetime.now().isoformat(),
        notes=product_data.get("notes", ""),
    )

    if context:
        score.compute_derived_flags(**context)

    result = asdict(score)
    result["composite_score"] = score.composite_score

    # Save score
    out_path = PROCESSED_DIR / f"score_{score.product_id}_{datetime.now().strftime('%Y%m%d')}.json"
    out_path.write_text(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    # Example scoring
    example = {
        "product_id": "PROD_EXAMPLE",
        "product_name": "Example ADC for Ovarian Cancer",
        "evidence_maturity": 3,
        "endpoint_clarity": 4,
        "trial_design_quality": 3,
        "regulatory_advantage": 4,
        "unmet_need_severity": 5,
        "mechanism_plausibility": 4,
        "manufacturing_complexity_risk": 3,
        "safety_uncertainty": 3,
        "sponsor_disclosure_quality": 3,
        "near_term_catalyst_density": 4,
    }

    context = {
        "num_competitors_in_indication": 3,
        "has_official_fda_date": False,
        "is_single_catalyst_company": True,
        "is_first_in_class": False,
        "has_multi_indication_potential": True,
    }

    result = score_product(example, context)
    print(f"Composite Score: {result['composite_score']:.1f}/100")
    print(f"Binary Event Risk: {result['binary_event_risk']}")
    print(f"Regulatory Visibility: {result['regulatory_visibility']}")
    print(f"Science Readthrough: {result['science_readthrough_value']}")
    print(f"Crowded Indication: {result['crowded_indication_penalty']}")
    print(f"Approval Complexity: {result['approval_path_complexity']}")
