"""
Constraint-based carbon optimization (item 11): given a target kg
CO2e/day, recommend the smallest set of lifestyle-lever changes
(commute mode, diet, energy usage) that gets a user from their current
personal baseline to that target -- greedily picking the
highest-kg-saved-per-day lever first, which favors the least number of
disruptive changes rather than claiming true global optimality.

This intentionally stays a plain greedy selection over a small, fixed
action catalog -- a real knapsack/ILP solver would be overkill for
three levers, and a future team wanting genuine multi-constraint
optimization (cost, effort, feasibility) has a clear seam to extend
`_candidate_actions` without touching the rest of the app.
"""

from collections import Counter
from dataclasses import dataclass
from statistics import mean

from .emission_factors import (
    DIET_FACTORS_KG_PER_DAY,
    ENERGY_LEVEL_KWH,
    get_region,
    population_defaults_kg_per_day,
)

ENERGY_TIER_DOWN = {"high": "medium", "medium": "low"}


@dataclass
class Action:
    lever: str
    change: str
    kg_saved_per_day: float
    rationale: str


def _current_commute(region: dict, history: list) -> tuple[str, float, float]:
    """Returns (mode, avg_distance_km, current_kg_per_day)."""
    with_mode = [h for h in history if h.commute_mode and h.commute_distance_km is not None]
    if not with_mode:
        # No commute history yet -- fall back to the same assumption
        # used for the population-default estimate, so the optimizer
        # still has something actionable to say to a brand-new user.
        return "car", 12.0, round(region["commute_kg_per_km"]["car"] * 12.0, 2)

    mode = Counter(h.commute_mode for h in with_mode).most_common(1)[0][0]
    distances = [h.commute_distance_km for h in with_mode if h.commute_mode == mode]
    avg_distance = mean(distances)
    return mode, avg_distance, round(region["commute_kg_per_km"][mode] * avg_distance, 2)


def _current_diet(history: list) -> tuple[str, float]:
    with_diet = [h.diet_type for h in history if h.diet_type]
    diet = Counter(with_diet).most_common(1)[0][0] if with_diet else "average"
    return diet, DIET_FACTORS_KG_PER_DAY[diet]


def _current_energy(region: dict, history: list) -> tuple[float, str | None]:
    """Returns (current_kg_per_day, current_level_if_level_based)."""
    kwh_entries = [h.energy_kwh for h in history if h.energy_kwh is not None]
    if kwh_entries:
        return round(mean(kwh_entries) * region["energy_kg_per_kwh"], 2), None

    level_entries = [h.energy_level for h in history if h.energy_level]
    if level_entries:
        level = Counter(level_entries).most_common(1)[0][0]
        return round(ENERGY_LEVEL_KWH[level] * region["energy_kg_per_kwh"], 2), level

    defaults = population_defaults_kg_per_day(region.get("_code", "IN"))
    return defaults["energy"], "medium"


def _candidate_actions(region: dict, region_code: str, history: list) -> tuple[list[Action], float]:
    commute_mode, commute_distance, commute_kg = _current_commute(region, history)
    diet, diet_kg = _current_diet(history)
    energy_kg, energy_level = _current_energy(region, history)

    baseline = round(commute_kg + diet_kg + energy_kg, 2)
    actions: list[Action] = []

    current_commute_factor = region["commute_kg_per_km"][commute_mode]
    for alt_mode, alt_factor in region["commute_kg_per_km"].items():
        if alt_mode == commute_mode or alt_factor >= current_commute_factor:
            continue
        saved = round((current_commute_factor - alt_factor) * commute_distance, 2)
        if saved <= 0.01:
            continue
        actions.append(
            Action(
                lever="commute",
                change=f"{commute_mode} → {alt_mode}",
                kg_saved_per_day=saved,
                rationale=f"Your ~{commute_distance:.0f}km commute costs less as {alt_mode}.",
            )
        )

    current_diet_kg = DIET_FACTORS_KG_PER_DAY[diet]
    for alt_diet, alt_kg in DIET_FACTORS_KG_PER_DAY.items():
        if alt_diet == diet or alt_kg >= current_diet_kg:
            continue
        saved = round(current_diet_kg - alt_kg, 2)
        actions.append(
            Action(
                lever="food",
                change=f"{diet} → {alt_diet}",
                kg_saved_per_day=saved,
                rationale=f"Shifting your typical diet from {diet} to {alt_diet}.",
            )
        )

    if energy_level and energy_level in ENERGY_TIER_DOWN:
        lower = ENERGY_TIER_DOWN[energy_level]
        saved = round((ENERGY_LEVEL_KWH[energy_level] - ENERGY_LEVEL_KWH[lower]) * region["energy_kg_per_kwh"], 2)
        actions.append(
            Action(
                lever="energy",
                change=f"{energy_level} usage → {lower} usage",
                kg_saved_per_day=saved,
                rationale="Cutting household energy use by one usage tier.",
            )
        )
    else:
        saved = round(energy_kg * 0.2, 2)
        if saved > 0.01:
            actions.append(
                Action(
                    lever="energy",
                    change="~20% efficiency improvement",
                    kg_saved_per_day=saved,
                    rationale="A general efficiency cut (LEDs, standby power, thermostat) on your logged usage.",
                )
            )

    actions.sort(key=lambda a: a.kg_saved_per_day, reverse=True)
    return actions, baseline


def optimize(history: list, target_kg_per_day: float, region_code: str) -> dict:
    region = dict(get_region(region_code))
    region["_code"] = region_code
    actions, baseline = _candidate_actions(region, region_code, history)

    chosen: list[Action] = []
    running_total = baseline
    for action in actions:
        if running_total <= target_kg_per_day:
            break
        chosen.append(action)
        running_total = round(running_total - action.kg_saved_per_day, 2)

    return {
        "baseline_kg_per_day": baseline,
        "target_kg_per_day": target_kg_per_day,
        "projected_kg_per_day": running_total,
        "achievable": running_total <= target_kg_per_day,
        "actions": chosen,
    }
