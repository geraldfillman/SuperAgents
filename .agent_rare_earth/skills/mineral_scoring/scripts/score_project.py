"""
Mineral Scoring -- Score mining projects on four dimensions.
Resource (0-10), Permitting (0-10), Offtake (0-10), Financial (0-10).
Overall score is the weighted average.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

PROCESSED_DIR = Path("data/processed/rare_earth/scores")


@dataclass
class ProjectScore:
    """Score a mining project on four key dimensions (0-10 scale)."""

    project_id: str = ""
    project_name: str = ""
    company_name: str = ""

    # Primary scoring dimensions (0-10)
    resource_score: int = 0
    permitting_score: int = 0
    offtake_score: int = 0
    financial_score: int = 0

    # Metadata
    scored_by: str = ""
    scored_at: str = ""
    notes: str = ""

    @property
    def overall_score(self) -> float:
        """Weighted overall score (0-10 scale)."""
        weights = {
            "resource": 0.30,
            "permitting": 0.25,
            "offtake": 0.25,
            "financial": 0.20,
        }
        total = (
            self.resource_score * weights["resource"]
            + self.permitting_score * weights["permitting"]
            + self.offtake_score * weights["offtake"]
            + self.financial_score * weights["financial"]
        )
        return round(total, 2)


def _score_resource(project_data: dict) -> int:
    """
    Score resource quality based on available data.
    Factors: reporting standard, category mix, grade, contained metal.
    """
    score = 0
    standard = project_data.get("reporting_standard", "").upper()
    if standard in ("NI_43_101", "JORC", "S-K_1300"):
        score += 3
    elif standard:
        score += 1

    has_measured = project_data.get("has_measured", False)
    has_indicated = project_data.get("has_indicated", False)
    has_inferred = project_data.get("has_inferred", False)

    if has_measured and has_indicated:
        score += 4
    elif has_indicated:
        score += 2
    elif has_inferred:
        score += 1

    contained_tonnes = project_data.get("contained_metal_tonnes", 0)
    if contained_tonnes > 100000:
        score += 3
    elif contained_tonnes > 10000:
        score += 2
    elif contained_tonnes > 0:
        score += 1

    return min(score, 10)


def _score_permitting(project_data: dict) -> int:
    """
    Score permitting progress.
    Factors: ROD issued, EIS completed, key permits in hand.
    """
    score = 0
    has_rod = project_data.get("has_rod", False)
    has_eis = project_data.get("has_eis", False)
    has_deis = project_data.get("has_deis", False)
    has_water_permit = project_data.get("has_water_permit", False)
    has_air_permit = project_data.get("has_air_permit", False)

    if has_rod:
        score += 4
    elif has_eis:
        score += 3
    elif has_deis:
        score += 2

    if has_water_permit:
        score += 2
    if has_air_permit:
        score += 2

    # Pending litigation reduces score
    if project_data.get("pending_litigation", False):
        score -= 2

    return max(0, min(score, 10))


def _score_offtake(project_data: dict) -> int:
    """
    Score offtake coverage.
    Factors: binding agreements, volume coverage, counterparty quality.
    """
    score = 0
    binding_count = project_data.get("binding_offtake_count", 0)
    nonbinding_count = project_data.get("nonbinding_offtake_count", 0)
    volume_coverage_pct = project_data.get("volume_coverage_pct", 0)

    if binding_count >= 2:
        score += 4
    elif binding_count >= 1:
        score += 3
    elif nonbinding_count >= 1:
        score += 1

    if volume_coverage_pct >= 80:
        score += 4
    elif volume_coverage_pct >= 50:
        score += 3
    elif volume_coverage_pct >= 25:
        score += 2
    elif volume_coverage_pct > 0:
        score += 1

    if project_data.get("has_government_offtake", False):
        score += 2

    return min(score, 10)


def _score_financial(project_data: dict) -> int:
    """
    Score financial health.
    Factors: cash runway, DPA funding, going concern flags.
    """
    score = 0
    runway_months = project_data.get("est_runway_months", 0)
    has_dpa_funding = project_data.get("has_dpa_funding", False)
    going_concern = project_data.get("going_concern_flag", False)

    if going_concern:
        return 1

    if runway_months >= 24:
        score += 5
    elif runway_months >= 12:
        score += 3
    elif runway_months >= 6:
        score += 2
    elif runway_months > 0:
        score += 1

    if has_dpa_funding:
        score += 3

    capex_funded_pct = project_data.get("capex_funded_pct", 0)
    if capex_funded_pct >= 75:
        score += 2
    elif capex_funded_pct >= 50:
        score += 1

    return min(score, 10)


def score_project(project_data: dict) -> dict:
    """
    Score a mining project across all four dimensions and return the assessment.

    Args:
        project_data: Dict with project attributes for scoring.

    Returns:
        Full score record with individual and overall scores.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    ps = ProjectScore(
        project_id=project_data.get("project_id", ""),
        project_name=project_data.get("project_name", ""),
        company_name=project_data.get("company_name", ""),
        resource_score=_score_resource(project_data),
        permitting_score=_score_permitting(project_data),
        offtake_score=_score_offtake(project_data),
        financial_score=_score_financial(project_data),
        scored_by=project_data.get("scored_by", "agent"),
        scored_at=datetime.now().isoformat(),
        notes=project_data.get("notes", ""),
    )

    result = asdict(ps)
    result["overall_score"] = ps.overall_score
    result["source_url"] = project_data.get("source_url", "")
    result["source_type"] = "derived"
    result["source_confidence"] = "secondary"

    # Save score
    out_path = PROCESSED_DIR / f"score_{ps.project_id}_{datetime.now().strftime('%Y%m%d')}.json"
    out_path.write_text(json.dumps(result, indent=2))

    return result


def score_all_projects() -> list[dict]:
    """Score all projects from processed data directories."""
    projects_dir = Path("data/processed/rare_earth")
    results = []

    # Load project data from various sources and score each
    # In production, this would read from a database or consolidated project file
    projects_file = projects_dir / "projects_master.json"
    if not projects_file.exists():
        print("No projects_master.json found. Run data collection first.")
        return results

    projects = json.loads(projects_file.read_text())
    if not isinstance(projects, list):
        projects = [projects]

    for project in projects:
        result = score_project(project)
        results.append(result)
        print(
            f"  [{result['project_name']}] "
            f"R={result['resource_score']} P={result['permitting_score']} "
            f"O={result['offtake_score']} F={result['financial_score']} "
            f"-> Overall={result['overall_score']}"
        )

    return results


if __name__ == "__main__":
    # Example scoring
    example = {
        "project_id": "PROJ_EXAMPLE",
        "project_name": "Mountain Pass REE Mine",
        "company_name": "Example Mining Corp",
        "reporting_standard": "S-K_1300",
        "has_measured": True,
        "has_indicated": True,
        "has_inferred": True,
        "contained_metal_tonnes": 50000,
        "has_rod": True,
        "has_eis": True,
        "has_deis": True,
        "has_water_permit": True,
        "has_air_permit": False,
        "pending_litigation": False,
        "binding_offtake_count": 1,
        "nonbinding_offtake_count": 2,
        "volume_coverage_pct": 60,
        "has_government_offtake": True,
        "est_runway_months": 18,
        "has_dpa_funding": True,
        "going_concern_flag": False,
        "capex_funded_pct": 55,
    }

    result = score_project(example)
    print(f"Overall Score: {result['overall_score']}/10")
    print(f"  Resource:   {result['resource_score']}/10")
    print(f"  Permitting: {result['permitting_score']}/10")
    print(f"  Offtake:    {result['offtake_score']}/10")
    print(f"  Financial:  {result['financial_score']}/10")
