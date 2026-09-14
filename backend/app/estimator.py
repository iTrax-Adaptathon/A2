"""
Core estimation logic: turns a (possibly incomplete) day's raw log into
a consistent kg CO2e figure per category.

This is the piece the problem statement's "Core Challenge" is actually
about, so it's kept in its own module with no FastAPI/DB imports --
a future team should be able to unit-test or replace this file alone.

Strategy for a missing field on a given day:
  1. "logged"    -- the user gave enough info this category can be computed directly.
  2. "estimated" -- missing, but the user has enough personal history in this
                    category that we can fall back to THEIR average instead of
                    guessing blind. Keeps trends meaningful instead of
                    punishing a day with zeros just because logging was partial.
  3. "default"   -- no personal history exists yet (e.g. first-ever log), so we
                    fall back to a population average just so the number isn't
                    misleadingly zero.

Every result carries its `source` so the frontend can visually distinguish
real data from inferred data rather than presenting a guess as fact.
"""

from dataclasses import dataclass
from statistics import mean
from typing import Iterable, Literal, Optional

from .emission_factors import (
    COMMUTE_FACTORS_KG_PER_KM,
    DIET_FACTORS_KG_PER_DAY,
    ENERGY_FACTOR_KG_PER_KWH,
    ENERGY_LEVEL_KWH,
    POPULATION_DEFAULT_KG_PER_DAY,
)

# How many of the user's own most-recent data points to average for
# the "estimated" fallback. Keeps the personal average responsive to
# recent lifestyle changes rather than drifting on months-old data.
ROLLING_WINDOW = 14

Source = Literal["logged", "estimated", "default"]


@dataclass
class CategoryResult:
    kg_co2e: float
    source: Source


def _raw_commute_kg(mode: Optional[str], distance_km: Optional[float]) -> Optional[float]:
    if mode is None or distance_km is None:
        return None
    return COMMUTE_FACTORS_KG_PER_KM[mode] * distance_km


def _raw_food_kg(diet_type: Optional[str]) -> Optional[float]:
    if diet_type is None:
        return None
    return DIET_FACTORS_KG_PER_DAY[diet_type]


def _raw_energy_kg(energy_kwh: Optional[float], energy_level: Optional[str]) -> Optional[float]:
    if energy_kwh is not None:
        return energy_kwh * ENERGY_FACTOR_KG_PER_KWH
    if energy_level is not None:
        return ENERGY_LEVEL_KWH[energy_level] * ENERGY_FACTOR_KG_PER_KWH
    return None


def _resolve(raw: Optional[float], personal_history: Iterable[float], category: str) -> CategoryResult:
    """`personal_history` must already be most-recent-first; only the
    first ROLLING_WINDOW values are used."""
    if raw is not None:
        return CategoryResult(kg_co2e=round(raw, 2), source="logged")

    history = list(personal_history)[:ROLLING_WINDOW]
    if history:
        return CategoryResult(kg_co2e=round(mean(history), 2), source="estimated")

    return CategoryResult(
        kg_co2e=round(POPULATION_DEFAULT_KG_PER_DAY[category], 2), source="default"
    )


def estimate_entry(entry, history: Iterable) -> dict:
    """
    entry: the LogEntry being estimated (ORM object or anything with the
           same attribute names).
    history: other LogEntry rows for this user, most-recent-date-first,
             used to build the personal rolling average per category.
             `entry` itself should not be included.
    """
    history = list(history)

    commute_history = [
        v
        for h in history
        if (v := _raw_commute_kg(h.commute_mode, h.commute_distance_km)) is not None
    ]
    food_history = [v for h in history if (v := _raw_food_kg(h.diet_type)) is not None]
    energy_history = [
        v
        for h in history
        if (v := _raw_energy_kg(h.energy_kwh, h.energy_level)) is not None
    ]

    commute = _resolve(
        _raw_commute_kg(entry.commute_mode, entry.commute_distance_km),
        commute_history,
        "commute",
    )
    food = _resolve(_raw_food_kg(entry.diet_type), food_history, "food")
    energy = _resolve(
        _raw_energy_kg(entry.energy_kwh, entry.energy_level), energy_history, "energy"
    )

    total = round(commute.kg_co2e + food.kg_co2e + energy.kg_co2e, 2)

    return {"commute": commute, "food": food, "energy": energy, "total_kg_co2e": total}
