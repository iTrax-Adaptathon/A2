"""
Given a target kg CO2e/day, recommends the smallest set of lifestyle-
lever changes (commute mode, diet, energy usage, shopping level) that
gets a user from their current baseline to that target -- picking the
highest-kg-saved-per-day lever first. That favors the fewest number of
changes rather than any claim of true global optimality.

Flights are counted in the baseline (amortized across the log window,
see `_amortized_flights_kg_per_day`) but not offered as a lever -- a
flight already happened, there's no daily habit to swap it for.

Just a greedy selection over a small, fixed action catalog. A real
solver would be overkill for four levers; `_candidate_actions` is the
place to extend this if that ever changes.
"""

from collections import Counter
from dataclasses import dataclass
from statistics import mean

from .emission_factors import (
    DIET_FACTORS_KG_PER_DAY,
    ENERGY_LEVEL_KWH,
    FLIGHT_FACTORS_KG_PER_KM,
    SHOPPING_LEVEL_KG_PER_DAY,
    get_region,
    population_defaults_kg_per_day,
)

ENERGY_TIER_DOWN = {"high": "medium", "medium": "low"}
SHOPPING_TIER_DOWN = {"high": "medium", "medium": "low"}


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


def _current_shopping(region_code: str, history: list) -> tuple[float, str]:
    """Returns (current_kg_per_day, current_level)."""
    level_entries = [h.shopping_level for h in history if getattr(h, "shopping_level", None)]
    if level_entries:
        level = Counter(level_entries).most_common(1)[0][0]
        return SHOPPING_LEVEL_KG_PER_DAY[level], level

    defaults = population_defaults_kg_per_day(region_code)
    return defaults["shopping"], "medium"


def _amortized_flights_kg_per_day(history: list) -> float:
    """Flights are event-based (see estimator.py), so their fair share
    of a *daily* baseline is total flight emissions spread over every
    day in the log window, not the average of only the days flown --
    otherwise a single long-haul trip would look like a daily habit.
    Not offered as an optimizer lever (see module docstring): there's
    no "smaller" lever for a trip that already happened."""
    if not history:
        return 0.0
    total = sum(
        FLIGHT_FACTORS_KG_PER_KM[h.flight_haul] * h.flight_km
        for h in history
        if getattr(h, "flight_km", None) is not None and getattr(h, "flight_haul", None) is not None
    )
    return round(total / len(history), 2)


def _candidate_actions(region: dict, region_code: str, history: list) -> tuple[list[Action], float]:
    commute_mode, commute_distance, commute_kg = _current_commute(region, history)
    diet, diet_kg = _current_diet(history)
    energy_kg, energy_level = _current_energy(region, history)
    shopping_kg, shopping_level = _current_shopping(region_code, history)
    flights_kg = _amortized_flights_kg_per_day(history)

    baseline = round(commute_kg + diet_kg + energy_kg + shopping_kg + flights_kg, 2)
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

    if shopping_level in SHOPPING_TIER_DOWN:
        lower = SHOPPING_TIER_DOWN[shopping_level]
        saved = round(SHOPPING_LEVEL_KG_PER_DAY[shopping_level] - SHOPPING_LEVEL_KG_PER_DAY[lower], 2)
        actions.append(
            Action(
                lever="shopping",
                change=f"{shopping_level} consumption → {lower} consumption",
                kg_saved_per_day=saved,
                rationale="Buying fewer new goods / choosing lower-impact ones.",
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
