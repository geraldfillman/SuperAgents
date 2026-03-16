"""
Project Scoring -- Score projects on 4 dimensions (0-10 each).
Interconnection, offtake, IRA credit, and financial health.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

PROCESSED_DIR = Path("data/processed/renewable_energy/scores")


@dataclass
class ProjectScore:
    """Score a renewable energy project on 4 dimensions (0-10 scale)."""

    project_id: str = ""
    project_name: str = ""
    project_type: str = ""       # solar / wind / battery / storage

    # Primary scoring dimensions (0-10)
    interconnection_score: float = 0.0
    offtake_score: float = 0.0
    credit_score: float = 0.0
    financial_score: float = 0.0

    # Metadata
    scored_by: str = ""
    scored_at: str = ""
    notes: str = ""

    @property
    def overall_score(self) -> float:
        """Weighted overall score (0-10)."""
        weights = {
            "interconnection": 0.30,
            "offtake": 0.30,
            "credit": 0.20,
            "financial": 0.20,
        }
        weighted = (
            self.interconnection_score * weights["interconnection"]
            + self.offtake_score * weights["offtake"]
            + self.credit_score * weights["credit"]
            + self.financial_score * weights["financial"]
        )
        return round(weighted, 2)


def score_interconnection(project_data: dict) -> float:
    """
    Score interconnection readiness (0-10).

    Factors: queue position, study completion, GIA executed, ISO region congestion.
    """
    score = 0.0
    stage = project_data.get("interconnection_stage", "").lower()

    if stage == "gia_executed":
        score = 9.0
    elif stage == "facilities_study_complete":
        score = 7.0
    elif stage == "system_impact_study_complete":
        score = 5.0
    elif stage == "feasibility_study_complete":
        score = 3.0
    elif stage == "in_queue":
        score = 1.0

    # Bonus for favorable ISO region (less congested)
    iso = project_data.get("iso_region", "").upper()
    if iso in ("ERCOT", "SPP"):
        score = min(10.0, score + 1.0)

    return round(score, 1)


def score_offtake(project_data: dict) -> float:
    """
    Score offtake / PPA quality (0-10).

    Factors: PPA executed, creditworthy offtaker, price, duration.
    """
    score = 0.0

    if project_data.get("ppa_executed"):
        score = 6.0
        duration = project_data.get("ppa_duration_years", 0)
        if duration >= 20:
            score += 2.0
        elif duration >= 10:
            score += 1.0

        # Creditworthy offtaker bonus
        if project_data.get("offtaker_investment_grade"):
            score += 2.0
    elif project_data.get("ppa_in_negotiation"):
        score = 3.0

    return min(10.0, round(score, 1))


def score_credit(project_data: dict) -> float:
    """
    Score IRA credit position (0-10).

    Factors: credit type eligibility, certification status, estimated value.
    """
    score = 0.0
    credit_status = project_data.get("certification_status", "").lower()

    if credit_status == "certified":
        score = 9.0
    elif credit_status == "application_submitted":
        score = 6.0
    elif credit_status == "eligible":
        score = 4.0
    elif credit_status == "under_review":
        score = 3.0
    else:
        score = 1.0

    # Bonus for multiple credit types
    credit_types = project_data.get("credit_types", [])
    if len(credit_types) > 1:
        score = min(10.0, score + 1.0)

    return round(score, 1)


def score_financial(project_data: dict) -> float:
    """
    Score financial health of the parent company (0-10).

    Factors: cash runway, debt ratio, recent offerings.
    """
    score = 5.0  # Baseline
    runway_months = project_data.get("runway_months", 0)

    if runway_months >= 24:
        score = 9.0
    elif runway_months >= 12:
        score = 7.0
    elif runway_months >= 6:
        score = 4.0
    elif runway_months > 0:
        score = 2.0

    # Penalty for recent dilutive offering
    if project_data.get("recent_offering"):
        score = max(0.0, score - 1.5)

    # Bonus for investment-grade credit rating
    if project_data.get("investment_grade"):
        score = min(10.0, score + 1.0)

    return round(score, 1)


def score_project(project_data: dict) -> dict:
    """
    Score a project across all 4 dimensions and return the full assessment.

    Args:
        project_data: Dict with project attributes for scoring
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()

    ps = ProjectScore(
        project_id=project_data.get("project_id", ""),
        project_name=project_data.get("project_name", ""),
        project_type=project_data.get("project_type", ""),
        interconnection_score=score_interconnection(project_data),
        offtake_score=score_offtake(project_data),
        credit_score=score_credit(project_data),
        financial_score=score_financial(project_data),
        scored_by=project_data.get("scored_by", "agent"),
        scored_at=now.isoformat(),
        notes=project_data.get("notes", ""),
    )

    result = asdict(ps)
    result["overall_score"] = ps.overall_score

    # Save score
    out_path = (
        PROCESSED_DIR
        / f"score_{ps.project_id}_{now.strftime('%Y%m%d')}.json"
    )
    out_path.write_text(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    # Example scoring
    example = {
        "project_id": "PROJ_SOLAR_TX_001",
        "project_name": "Lone Star Solar Farm",
        "project_type": "solar",
        "interconnection_stage": "facilities_study_complete",
        "iso_region": "ERCOT",
        "ppa_executed": True,
        "ppa_duration_years": 15,
        "offtaker_investment_grade": True,
        "certification_status": "eligible",
        "credit_types": ["ITC"],
        "runway_months": 18,
        "recent_offering": False,
        "investment_grade": False,
    }

    result = score_project(example)
    print(f"Project: {result['project_name']}")
    print(f"  Interconnection: {result['interconnection_score']}/10")
    print(f"  Offtake:         {result['offtake_score']}/10")
    print(f"  Credit:          {result['credit_score']}/10")
    print(f"  Financial:       {result['financial_score']}/10")
    print(f"  Overall:         {result['overall_score']}/10")
