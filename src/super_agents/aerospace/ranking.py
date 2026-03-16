"""Watchlist ranking helpers built on top of company scorecards."""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

from .io_utils import write_json
from .paths import DASHBOARDS_DIR, ensure_directory, slugify
from .scorecards import build_company_scorecards

RANKING_WEIGHTS = {
    "awards": 0.25,
    "procurement": 0.2,
    "execution": 0.2,
    "budget": 0.15,
    "financial": 0.1,
    "insider": 0.1,
}


def _scale_log(value: float, max_value: float) -> float:
    if value <= 0 or max_value <= 0:
        return 0.0
    return min(1.0, math.log10(value + 1.0) / math.log10(max_value + 1.0))


def _scale_ratio(value: float, max_value: float) -> float:
    if value <= 0 or max_value <= 0:
        return 0.0
    return min(1.0, value / max_value)


def _financial_score(scorecard: dict) -> float:
    if scorecard.get("going_concern_flag"):
        return 0.0

    runway = scorecard.get("est_runway_months")
    if runway is None:
        return 0.6 if scorecard.get("latest_financial_report_date") else 0.25

    runway_value = float(runway)
    if runway_value >= 24:
        return 1.0
    if runway_value >= 18:
        return 0.8
    if runway_value >= 12:
        return 0.6
    if runway_value >= 6:
        return 0.3
    return 0.1


def _insider_score(scorecard: dict) -> float:
    purchase_value = float(scorecard.get("insider_purchase_value_usd", 0.0) or 0.0)
    sale_value = float(scorecard.get("insider_sale_value_usd", 0.0) or 0.0)
    gross_value = purchase_value + sale_value
    if gross_value <= 0:
        return 0.5
    ratio = (purchase_value - sale_value) / gross_value
    return max(0.0, min(1.0, 0.5 + 0.5 * ratio))


def _execution_score(scorecard: dict, *, max_milestones: int, max_test_events: int, max_faa_signals: int) -> float:
    latest_trl = scorecard.get("latest_trl_level")
    trl_component = (float(latest_trl) / 9.0) if latest_trl else 0.25
    milestone_component = _scale_ratio(float(scorecard.get("upcoming_milestone_count", 0) or 0), float(max_milestones))
    test_event_component = _scale_ratio(float(scorecard.get("test_event_count", 0) or 0), float(max_test_events))
    faa_component = _scale_ratio(float(scorecard.get("faa_signal_count", 0) or 0), float(max_faa_signals))
    return min(
        1.0,
        (trl_component * 0.5)
        + (milestone_component * 0.2)
        + (test_event_component * 0.15)
        + (faa_component * 0.15),
    )


def _candidate_budget_support_count(scorecard: dict) -> int:
    support_count = 0
    if (
        float(scorecard.get("contract_award_value_usd", 0.0) or 0.0) > 0
        or int(scorecard.get("contract_award_count", 0) or 0) > 0
        or float(scorecard.get("sbir_award_value_usd", 0.0) or 0.0) > 0
        or int(scorecard.get("sbir_award_count", 0) or 0) > 0
    ):
        support_count += 1
    if (
        int(scorecard.get("high_priority_signal_count", 0) or 0) > 0
        or int(scorecard.get("procurement_signal_count", 0) or 0) >= 2
        or int(scorecard.get("sam_pipeline_signal_count", 0) or 0) > 0
    ):
        support_count += 1
    if (
        int(scorecard.get("latest_trl_level", 0) or 0) >= 6
        or int(scorecard.get("upcoming_milestone_count", 0) or 0) > 0
        or int(scorecard.get("test_event_count", 0) or 0) > 0
        or int(scorecard.get("faa_signal_count", 0) or 0) > 0
    ):
        support_count += 1
    return support_count


def _candidate_budget_multiplier(scorecard: dict) -> float:
    support_count = _candidate_budget_support_count(scorecard)
    if float(scorecard.get("explicit_budget_exposure_usd", 0.0) or 0.0) > 0:
        if support_count >= 2:
            return 0.1
        if support_count == 1:
            return 0.05
        return 0.02
    if support_count >= 3:
        return 0.15
    if support_count == 2:
        return 0.1
    if support_count == 1:
        return 0.05
    return 0.0


def _effective_budget_value(scorecard: dict) -> float:
    explicit_value = float(scorecard.get("explicit_budget_exposure_usd", 0.0) or 0.0)
    candidate_value = float(scorecard.get("candidate_budget_exposure_usd", 0.0) or 0.0)
    return explicit_value + (candidate_value * _candidate_budget_multiplier(scorecard))


def _budget_score(scorecard: dict, *, max_budget_signal: float) -> float:
    explicit_value = float(scorecard.get("explicit_budget_exposure_usd", 0.0) or 0.0)
    effective_value = _effective_budget_value(scorecard)
    score = _scale_log(effective_value, max_budget_signal)
    if explicit_value > 0:
        score = min(1.0, score + 0.1)
    return score


def _build_reasons(scorecard: dict, components: dict[str, float]) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    risks: list[str] = []

    if scorecard.get("contract_award_value_usd", 0.0):
        reasons.append(f"award activity ${scorecard['contract_award_value_usd']:,.0f}")
    if scorecard.get("sbir_award_value_usd", 0.0):
        reasons.append(f"SBIR awards ${scorecard['sbir_award_value_usd']:,.0f}")
    if scorecard.get("high_priority_signal_count", 0):
        reasons.append(f"{scorecard['high_priority_signal_count']} high-priority procurement signal(s)")
    if scorecard.get("sam_pipeline_signal_count", 0):
        reasons.append(f"{scorecard['sam_pipeline_signal_count']} SAM pipeline signal(s)")
    if scorecard.get("faa_high_priority_signal_count", 0):
        reasons.append(f"{scorecard['faa_high_priority_signal_count']} FAA licensing signal(s)")
    elif scorecard.get("faa_signal_count", 0):
        reasons.append(f"{scorecard['faa_signal_count']} FAA stakeholder/licensing signal(s)")
    if scorecard.get("explicit_budget_exposure_usd", 0.0):
        reasons.append(f"explicit budget exposure ${scorecard['explicit_budget_exposure_usd']:,.0f}")
    if scorecard.get("latest_trl_level"):
        reasons.append(f"latest TRL {scorecard['latest_trl_level']}")
    if scorecard.get("est_runway_months"):
        reasons.append(f"estimated runway {scorecard['est_runway_months']} months")

    if scorecard.get("going_concern_flag"):
        risks.append("going concern flag")
    if scorecard.get("insider_sale_value_usd", 0.0) and components["insider"] < 0.3:
        risks.append(f"insider sales ${scorecard['insider_sale_value_usd']:,.0f}")
    if not scorecard.get("latest_financial_report_date"):
        risks.append("no current financial snapshot")
    if scorecard.get("budget_match_count", 0) and not scorecard.get("explicit_budget_exposure_usd", 0.0):
        if _candidate_budget_support_count(scorecard) == 0:
            risks.append("candidate budget links are uncorroborated")
        else:
            risks.append("budget links are still candidate-only")

    return reasons[:3], risks[:3]


def build_watchlist_ranking(
    *,
    scorecard_bundle: dict | None = None,
    min_budget_score: float = 0.35,
) -> dict:
    """Rank the watchlist using the current scorecard bundle."""
    bundle = scorecard_bundle or build_company_scorecards(min_budget_score=min_budget_score)
    scorecards = list(bundle.get("company_scorecards", []))

    max_award_value = max((float(record.get("contract_award_value_usd", 0.0) or 0.0) for record in scorecards), default=0.0)
    max_award_value = max(
        (
            float(record.get("contract_award_value_usd", 0.0) or 0.0)
            + float(record.get("sbir_award_value_usd", 0.0) or 0.0)
            for record in scorecards
        ),
        default=max_award_value,
    )
    max_award_count = max(
        (
            int(record.get("contract_award_count", 0) or 0)
            + int(record.get("sbir_award_count", 0) or 0)
            for record in scorecards
        ),
        default=0,
    )
    max_signal_count = max((int(record.get("high_priority_signal_count", 0) or 0) for record in scorecards), default=0)
    max_procurement_count = max((int(record.get("procurement_signal_count", 0) or 0) for record in scorecards), default=0)
    max_pipeline_count = max((int(record.get("sam_pipeline_signal_count", 0) or 0) for record in scorecards), default=0)
    max_milestones = max((int(record.get("upcoming_milestone_count", 0) or 0) for record in scorecards), default=0)
    max_test_events = max((int(record.get("test_event_count", 0) or 0) for record in scorecards), default=0)
    max_faa_signals = max((int(record.get("faa_signal_count", 0) or 0) for record in scorecards), default=0)
    max_budget_signal = max(
        (_effective_budget_value(record) for record in scorecards),
        default=0.0,
    )

    rankings: list[dict] = []
    for scorecard in scorecards:
        award_value_total = float(scorecard.get("contract_award_value_usd", 0.0) or 0.0) + float(
            scorecard.get("sbir_award_value_usd", 0.0) or 0.0
        )
        award_count_total = int(scorecard.get("contract_award_count", 0) or 0) + int(
            scorecard.get("sbir_award_count", 0) or 0
        )
        awards_score = min(
            1.0,
            (_scale_log(award_value_total, max_award_value) * 0.7)
            + (_scale_ratio(float(award_count_total), float(max_award_count)) * 0.3),
        )
        procurement_score = min(
            1.0,
            (_scale_ratio(float(scorecard.get("high_priority_signal_count", 0) or 0), float(max_signal_count)) * 0.5)
            + (_scale_ratio(float(scorecard.get("procurement_signal_count", 0) or 0), float(max_procurement_count)) * 0.25)
            + (_scale_ratio(float(scorecard.get("sam_pipeline_signal_count", 0) or 0), float(max_pipeline_count)) * 0.25),
        )
        execution_score = _execution_score(
            scorecard,
            max_milestones=max_milestones,
            max_test_events=max_test_events,
            max_faa_signals=max_faa_signals,
        )
        budget_score = _budget_score(scorecard, max_budget_signal=max_budget_signal)
        financial_score = _financial_score(scorecard)
        insider_score = _insider_score(scorecard)

        components = {
            "awards": awards_score,
            "procurement": procurement_score,
            "execution": execution_score,
            "budget": budget_score,
            "financial": financial_score,
            "insider": insider_score,
        }
        composite = sum(components[name] * weight for name, weight in RANKING_WEIGHTS.items())
        reasons, risks = _build_reasons(scorecard, components)

        rankings.append(
            {
                "company_name": scorecard["company_name"],
                "ticker": scorecard["ticker"],
                "priority": scorecard["priority"],
                "composite_score": round(composite * 100.0, 2),
                "score_components": {name: round(value * 100.0, 2) for name, value in components.items()},
                "contract_award_count": scorecard["contract_award_count"],
                "contract_award_value_usd": scorecard["contract_award_value_usd"],
                "sbir_award_count": scorecard.get("sbir_award_count", 0),
                "sbir_award_value_usd": scorecard.get("sbir_award_value_usd", 0.0),
                "sam_pipeline_signal_count": scorecard.get("sam_pipeline_signal_count", 0),
                "faa_signal_count": scorecard.get("faa_signal_count", 0),
                "faa_high_priority_signal_count": scorecard.get("faa_high_priority_signal_count", 0),
                "high_priority_signal_count": scorecard["high_priority_signal_count"],
                "latest_trl_level": scorecard["latest_trl_level"],
                "explicit_budget_exposure_usd": scorecard["explicit_budget_exposure_usd"],
                "candidate_budget_exposure_usd": scorecard["candidate_budget_exposure_usd"],
                "budget_support_signal_count": _candidate_budget_support_count(scorecard),
                "est_runway_months": scorecard["est_runway_months"],
                "going_concern_flag": scorecard["going_concern_flag"],
                "insider_trade_count": scorecard["insider_trade_count"],
                "insider_sale_value_usd": scorecard["insider_sale_value_usd"],
                "insider_purchase_value_usd": scorecard["insider_purchase_value_usd"],
                "reasons": reasons,
                "risks": risks,
            }
        )

    rankings.sort(
        key=lambda record: (
            -record["composite_score"],
            {"high": 0, "medium": 1, "low": 2}.get(str(record.get("priority", "")).lower(), 3),
            record["ticker"],
        )
    )

    for index, record in enumerate(rankings, start=1):
        record["rank"] = index

    summary = {
        "ranked_companies": len(rankings),
        "top_ticker": rankings[0]["ticker"] if rankings else "",
        "top_score": rankings[0]["composite_score"] if rankings else 0.0,
        "companies_with_explicit_budget": sum(1 for record in rankings if record["explicit_budget_exposure_usd"] > 0),
        "companies_with_financials": sum(1 for record in rankings if record.get("est_runway_months") is not None or record.get("going_concern_flag") is not None),
    }

    return {
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "scoring_model": {
            "weights": RANKING_WEIGHTS,
            "notes": [
                "Budget uses explicit exposure plus a corroboration-gated candidate contribution.",
                "Financials fall back to a neutral-positive score when a current report exists but runway is not estimated.",
                "Insider score penalizes sale-heavy activity and rewards purchase-heavy activity.",
                "FAA licensing and stakeholder page signals contribute execution support for smaller space names.",
            ],
        },
        "rankings": rankings,
    }


def save_watchlist_ranking(bundle: dict, *, label: str = "watchlist") -> Path:
    """Save ranked watchlist output to the dashboards folder."""
    out_path = ensure_directory(DASHBOARDS_DIR) / f"watchlist_ranking_{slugify(label)}.json"
    write_json(out_path, bundle)
    return out_path
