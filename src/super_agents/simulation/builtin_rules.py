"""Built-in scenario rules that drive variable evolution per tick.

These rules model how variables change over time in response to scenario
conditions. Without them, the engine only observes static state.

Each rule factory returns a ReasoningFn that:
  1. Reads the current variables from TickContext
  2. Applies domain logic to compute changes
  3. Returns an Assessment with variable_updates for the next tick

The engine merges all variable_updates at the end of each tick.
"""

from __future__ import annotations

from typing import Any

from .persona import Assessment, ReasoningFn, TickContext
from .scenario import PersonaConfig


# ---------------------------------------------------------------------------
# Oil price escalation (energy analyst)
# ---------------------------------------------------------------------------

def oil_crisis_rule(
    base_daily_increase: float = 4.5,
    spr_dampening: float = 0.4,
    max_price: float = 180.0,
) -> ReasoningFn:
    """Model oil price escalation during a supply disruption.

    - Price rises each tick proportional to disrupted supply
    - SPR release dampens the increase
    - Volatility decreases as market adjusts
    """
    def rule(config: PersonaConfig, ctx: TickContext) -> Assessment:
        vars_ = ctx.variables
        wti = float(vars_.get("oil_price_wti", 95))
        brent = float(vars_.get("oil_price_brent", 98))
        disrupted = float(vars_.get("daily_oil_disrupted_mbd", 0))
        spr_active = vars_.get("spr_release_active", False)
        tick = ctx.tick_number

        observations: list[str] = []
        predictions: list[dict[str, Any]] = []
        alerts: list[str] = []
        updates: dict[str, Any] = {}

        if disrupted <= 0:
            observations.append("No oil supply disruption detected")
            return _build(config, ctx, observations, predictions, alerts, updates, 0.5, "No disruption")

        # Price increase decays over time as market adapts (log curve)
        decay = max(0.3, 1.0 - (tick * 0.06))
        increase = base_daily_increase * decay * (disrupted / 21.0)

        if spr_active:
            increase *= (1 - spr_dampening)
            observations.append(f"SPR release active - dampening price rise by {spr_dampening:.0%}")

        new_wti = min(max_price, wti + increase)
        new_brent = min(max_price + 3, brent + increase * 1.03)  # Brent premium

        updates["oil_price_wti"] = round(new_wti, 2)
        updates["oil_price_brent"] = round(new_brent, 2)

        observations.append(f"WTI: ${wti:.2f} -> ${new_wti:.2f} (+${increase:.2f})")
        observations.append(f"Brent: ${brent:.2f} -> ${new_brent:.2f}")
        observations.append(f"Supply disrupted: {disrupted} mbd, decay factor: {decay:.2f}")

        # SPR trigger prediction
        if new_wti > 115 and not spr_active:
            predictions.append({
                "text": "SPR release imminent - WTI above $115",
                "variable": "oil_price_wti",
                "value": new_wti,
            })
            if new_wti > 120:
                updates["spr_release_active"] = True
                alerts.append(f"SPR ACTIVATED: WTI hit ${new_wti:.2f}")

        if new_wti > 140:
            alerts.append(f"CRITICAL: WTI at ${new_wti:.2f} - demand destruction zone")

        confidence = min(0.9, 0.6 + tick * 0.02)
        reasoning = (
            f"Oil escalation model: +${increase:.2f}/day "
            f"(base={base_daily_increase}, decay={decay:.2f}, disruption={disrupted}mbd)"
        )

        return _build(config, ctx, observations, predictions, alerts, updates, confidence, reasoning)

    return rule


# ---------------------------------------------------------------------------
# Shipping route diversion (logistics officer)
# ---------------------------------------------------------------------------

def route_diversion_rule(
    cape_daily_increase: float = 5.0,
    teu_daily_increase: float = 280,
    max_cape_pct: float = 95.0,
) -> ReasoningFn:
    """Model shipping route diversion when a chokepoint closes.

    - Cape of Good Hope utilization rises each day
    - TEU spot rates increase with congestion
    - Suez backflow absorbs some traffic
    """
    def rule(config: PersonaConfig, ctx: TickContext) -> Assessment:
        vars_ = ctx.variables
        strait_status = vars_.get("strait_status", "open")
        cape_pct = float(vars_.get("cape_route_utilization_pct", 40))
        suez_pct = float(vars_.get("suez_backflow_pct", 15))
        teu_rate = float(vars_.get("teu_spot_rate_eu_asia", 2800))
        tick = ctx.tick_number

        observations: list[str] = []
        predictions: list[dict[str, Any]] = []
        alerts: list[str] = []
        updates: dict[str, Any] = {}

        if strait_status == "open":
            observations.append("Strait open - normal routing")
            return _build(config, ctx, observations, predictions, alerts, updates, 0.5, "Normal ops")

        # Cape route fills up with diminishing returns near capacity
        capacity_pressure = max(0.2, 1.0 - (cape_pct / 100.0))
        cape_increase = cape_daily_increase * capacity_pressure
        new_cape = min(max_cape_pct, cape_pct + cape_increase)

        # Suez backflow grows slowly
        new_suez = min(35.0, suez_pct + 1.5)

        # TEU rates spike harder early, stabilize later
        rate_multiplier = 1.0 + (cape_pct / 100.0) * 0.5
        teu_increase = teu_daily_increase * rate_multiplier
        new_teu = teu_rate + teu_increase

        updates["cape_route_utilization_pct"] = round(new_cape, 1)
        updates["suez_backflow_pct"] = round(new_suez, 1)
        updates["teu_spot_rate_eu_asia"] = round(new_teu, 0)

        observations.append(f"Cape route: {cape_pct:.1f}% -> {new_cape:.1f}%")
        observations.append(f"Suez backflow: {suez_pct:.1f}% -> {new_suez:.1f}%")
        observations.append(f"TEU spot rate: ${teu_rate:.0f} -> ${new_teu:.0f}")

        if new_cape > 70:
            predictions.append({
                "text": "Cape route becoming dominant global route",
                "variable": "cape_route_utilization_pct",
                "value": new_cape,
            })

        if new_cape > 85:
            alerts.append(f"Cape route at {new_cape:.1f}% - congestion critical")

        if new_teu > 5000:
            alerts.append(f"TEU rate at ${new_teu:.0f} - shipping cost crisis")

        confidence = min(0.85, 0.55 + tick * 0.025)
        reasoning = (
            f"Route diversion: cape +{cape_increase:.1f}% "
            f"(pressure={capacity_pressure:.2f}), TEU +${teu_increase:.0f}"
        )

        return _build(config, ctx, observations, predictions, alerts, updates, confidence, reasoning)

    return rule


# ---------------------------------------------------------------------------
# Financial flight-to-safety (bond trader)
# ---------------------------------------------------------------------------

def flight_to_safety_rule(
    vix_daily_increase: float = 2.5,
    yield_daily_change: float = -0.04,
) -> ReasoningFn:
    """Model financial market reactions to geopolitical crisis.

    - VIX rises as uncertainty increases
    - Treasury yields drop as money flows to safety
    - Insurance markets freeze/reopen based on crisis duration
    """
    def rule(config: PersonaConfig, ctx: TickContext) -> Assessment:
        vars_ = ctx.variables
        vix = float(vars_.get("vix", 22))
        yield_10y = float(vars_.get("us_10y_yield", 4.25))
        insurance = vars_.get("insurance_market_status", "normal")
        strait_status = vars_.get("strait_status", "open")
        tick = ctx.tick_number

        observations: list[str] = []
        predictions: list[dict[str, Any]] = []
        alerts: list[str] = []
        updates: dict[str, Any] = {}

        if strait_status == "open":
            observations.append("Markets calm - no geopolitical trigger")
            return _build(config, ctx, observations, predictions, alerts, updates, 0.5, "Normal markets")

        # VIX spikes fast then slowly decays
        vix_spike = vix_daily_increase * max(0.4, 1.0 - (tick * 0.05))
        new_vix = min(65.0, vix + vix_spike)

        # Yields drop as money flows to treasuries
        yield_change = yield_daily_change * max(0.3, 1.0 - (tick * 0.04))
        new_yield = max(2.5, yield_10y + yield_change)

        # Insurance market lifecycle
        if tick < 2:
            new_insurance = "frozen"
        elif tick < 5:
            new_insurance = "restricted"
        elif tick < 10:
            new_insurance = "elevated_premiums"
        else:
            new_insurance = "stabilizing"

        updates["vix"] = round(new_vix, 1)
        updates["us_10y_yield"] = round(new_yield, 3)
        updates["insurance_market_status"] = new_insurance

        observations.append(f"VIX: {vix:.1f} -> {new_vix:.1f} (+{vix_spike:.1f})")
        observations.append(f"10Y yield: {yield_10y:.3f}% -> {new_yield:.3f}%")
        observations.append(f"Insurance: {insurance} -> {new_insurance}")

        if new_vix > 35:
            predictions.append({
                "text": "VIX above 35 - institutional hedging cascade",
                "variable": "vix",
                "value": new_vix,
            })

        if new_vix > 40:
            alerts.append(f"VIX at {new_vix:.1f} - CRISIS TERRITORY")

        confidence = min(0.85, 0.6 + tick * 0.02)
        reasoning = f"Flight-to-safety: VIX +{vix_spike:.1f}, yield {yield_change:+.4f}"

        return _build(config, ctx, observations, predictions, alerts, updates, confidence, reasoning)

    return rule


# ---------------------------------------------------------------------------
# Coalition military response (defense analyst)
# ---------------------------------------------------------------------------

def coalition_response_rule() -> ReasoningFn:
    """Model military coalition response timeline.

    - Response progresses through phases: pending -> assembling -> deploying -> active
    - Days since closure tracked
    """
    def rule(config: PersonaConfig, ctx: TickContext) -> Assessment:
        vars_ = ctx.variables
        response = vars_.get("coalition_response", "pending")
        days = int(vars_.get("days_since_closure", 0))
        strait_status = vars_.get("strait_status", "open")
        tick = ctx.tick_number

        observations: list[str] = []
        predictions: list[dict[str, Any]] = []
        alerts: list[str] = []
        updates: dict[str, Any] = {}

        if strait_status == "open":
            observations.append("No military escalation")
            return _build(config, ctx, observations, predictions, alerts, updates, 0.5, "Peacetime")

        new_days = days + 1
        updates["days_since_closure"] = new_days

        # Response phases
        if new_days <= 2:
            new_response = "assembling"
            observations.append(f"Day {new_days}: Coalition forces assembling, UN Security Council convening")
            predictions.append({"text": "Coalition deployment within 5-7 days", "timeline": "5-7 days"})
        elif new_days <= 5:
            new_response = "deploying"
            observations.append(f"Day {new_days}: Carrier groups en route, mine-clearing ops planned")
            alerts.append("Naval forces deploying - escalation risk HIGH")
        elif new_days <= 8:
            new_response = "active_operations"
            observations.append(f"Day {new_days}: Active mine-clearing and patrol operations")
            predictions.append({
                "text": "Partial strait reopening within 3-4 days",
                "variable": "strait_status",
            })
        elif new_days <= 11:
            new_response = "securing"
            observations.append(f"Day {new_days}: Strait partially secured, limited transit resuming")
            updates["strait_status"] = "restricted"
            updates["daily_oil_disrupted_mbd"] = max(5.0, float(vars_.get("daily_oil_disrupted_mbd", 21)) * 0.5)
        else:
            new_response = "stabilized"
            observations.append(f"Day {new_days}: Coalition presence established, transit normalizing")
            updates["strait_status"] = "restricted"
            updates["daily_oil_disrupted_mbd"] = max(2.0, float(vars_.get("daily_oil_disrupted_mbd", 5)) * 0.7)

        updates["coalition_response"] = new_response

        confidence = min(0.8, 0.5 + new_days * 0.03)
        reasoning = f"Coalition timeline: day {new_days}, phase: {new_response}"

        return _build(config, ctx, observations, predictions, alerts, updates, confidence, reasoning)

    return rule


# ---------------------------------------------------------------------------
# Auto-registration helper
# ---------------------------------------------------------------------------

# Maps scenario variable patterns to (persona_name_pattern, rule_factory) pairs
SCENARIO_RULE_REGISTRY: dict[str, list[tuple[str, str, ReasoningFn]]] = {
    "oil_price_wti": [
        ("energy", "oil_crisis", oil_crisis_rule()),
    ],
    "cape_route_utilization_pct": [
        ("logistics", "route_diversion", route_diversion_rule()),
    ],
    "vix": [
        ("bond", "flight_to_safety", flight_to_safety_rule()),
    ],
    "coalition_response": [
        ("defense", "coalition_response", coalition_response_rule()),
    ],
}


def auto_register(engine: Any, scenario: Any) -> int:
    """Automatically register relevant rules based on scenario variables.

    Matches variable names to rule factories, then assigns rules to
    personas whose names contain the expected pattern.

    Returns:
        Number of rules registered.
    """
    registered = 0
    variables = scenario.variables

    for var_name, rule_entries in SCENARIO_RULE_REGISTRY.items():
        if var_name not in variables:
            continue

        for persona_pattern, rule_name, rule_fn in rule_entries:
            for persona_name in engine.persona_names:
                if persona_pattern in persona_name:
                    try:
                        engine.register_rules(persona_name, [(rule_name, rule_fn)])
                        registered += 1
                    except ValueError:
                        pass

    return registered


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build(
    config: PersonaConfig,
    ctx: TickContext,
    observations: list[str],
    predictions: list[dict[str, Any]],
    alerts: list[str],
    updates: dict[str, Any],
    confidence: float,
    reasoning: str,
) -> Assessment:
    return Assessment(
        persona_name=config.name,
        tick_number=ctx.tick_number,
        tick_time=ctx.tick_time,
        observations=tuple(observations),
        predictions=tuple(predictions),
        variable_updates=updates,
        confidence=round(confidence, 3),
        reasoning=reasoning,
        alerts=tuple(alerts),
    )
