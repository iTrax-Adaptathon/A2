"""
Core estimation logic: turns a (possibly incomplete) day's raw log into
a consistent, uncertainty-aware kg CO2e figure per category, for a
given regional emission-factor profile.

Kept free of FastAPI/DB imports so it can be unit-tested or swapped
out on its own (see tests/test_estimator.py).

Source taxonomy (most to least certain):
  "observed"          -- an exact user-provided number (typed km, typed kWh,
                          a meter reading pulled off a receipt).
  "inferred"          -- derived from a channel that had to guess a gap, e.g.
                          natural-language/voice logging that named a mode
                          ("drove to work") without a distance, or an OCR'd
                          fuel receipt converted from litres to km.
  "personal_estimate" -- nothing logged this day, but the user has enough of
                          their OWN recent history in this category to fall
                          back to their personal average instead of guessing
                          blind or zeroing it out. Prefers a same-weekday
                          average when enough weekday-matched history exists
                          (a missing Tuesday first looks at other Tuesdays --
                          see `basis` below) before falling back to a flat
                          rolling average.
  "population_default" -- no data logged AND no personal history yet either
                          (e.g. day one), so a population-average constant is
                          used just so the number isn't misleadingly zero.

Each tier carries a rough uncertainty band, and the whole day's total
combines them via root-sum-of-squares (independent-error assumption)
rather than naive addition, so the range tightens as more categories
are directly observed.
"""

import math
from dataclasses import dataclass
from statistics import mean
from typing import Iterable, Literal, Optional

from .emission_factors import (
    DIET_FACTORS_KG_PER_DAY,
    ENERGY_LEVEL_KWH,
    FLIGHT_FACTORS_KG_PER_KM,
    SHOPPING_LEVEL_KG_PER_DAY,
    get_region,
    population_defaults_kg_per_day,
)

# How many of the user's own most-recent (by date) data points to
# average for the flat "personal_estimate" fallback.
ROLLING_WINDOW = 14

# Smart missing-data reconstruction: how far back (in history entries, not
# calendar days) to search for same-weekday matches, and the minimum count
# needed before trusting a weekday-specific average over the flat one. A
# missing Tuesday is a different animal from a missing Saturday -- most
# people's commute/energy/shopping genuinely vary by day of week -- but two
# data points isn't a pattern yet, hence the minimum.
WEEKDAY_LOOKBACK = 60
WEEKDAY_MIN_SAMPLES = 2

Source = Literal["observed", "inferred", "personal_estimate", "population_default"]

UNCERTAINTY_PCT = {
    "observed": 0.05,
    "inferred": 0.20,
    "personal_estimate": 0.30,
    "population_default": 0.50,
}


@dataclass
class CategoryResult:
    kg_co2e: float
    source: Source
    uncertainty_pct: float
    low_kg_co2e: float
    high_kg_co2e: float
    # Only meaningful when source == "personal_estimate": which
    # reconstruction strategy produced the number, so the UI can show
    # "Tue avg" instead of a generic "your average".
    basis: Optional[Literal["weekday_average", "rolling_average"]] = None


def _raw_commute_kg(region: dict, mode: Optional[str], distance_km: Optional[float]) -> Optional[float]:
    if mode is None or distance_km is None:
        return None
    return region["commute_kg_per_km"][mode] * distance_km


def _raw_food_kg(diet_type: Optional[str]) -> Optional[float]:
    if diet_type is None:
        return None
    return DIET_FACTORS_KG_PER_DAY[diet_type]


def _raw_energy_kg(region: dict, energy_kwh: Optional[float], energy_level: Optional[str]) -> Optional[float]:
    if energy_kwh is not None:
        return energy_kwh * region["energy_kg_per_kwh"]
    if energy_level is not None:
        return ENERGY_LEVEL_KWH[energy_level] * region["energy_kg_per_kwh"]
    return None


def _raw_flight_kg(flight_km: Optional[float], flight_haul: Optional[str]) -> Optional[float]:
    if flight_km is None or flight_haul is None:
        return None
    return FLIGHT_FACTORS_KG_PER_KM[flight_haul] * flight_km


def _raw_shopping_kg(shopping_level: Optional[str]) -> Optional[float]:
    if shopping_level is None:
        return None
    return SHOPPING_LEVEL_KG_PER_DAY[shopping_level]


def _band(kg: float, source: Source, basis: Optional[str] = None) -> CategoryResult:
    pct = UNCERTAINTY_PCT[source]
    delta = kg * pct
    return CategoryResult(
        kg_co2e=round(kg, 2),
        source=source,
        uncertainty_pct=pct,
        low_kg_co2e=round(max(kg - delta, 0), 2),
        high_kg_co2e=round(kg + delta, 2),
        basis=basis,
    )


def _resolve(
    raw: Optional[float],
    inferred: bool,
    dated_history: Iterable[tuple],
    default_kg: float,
    target_weekday: int,
    use_personal_average: bool = True,
) -> CategoryResult:
    """`dated_history` is an iterable of (date, raw_value) pairs, already
    most-recent-date-first.

    `inferred` marks that `raw` (if not None) came from a channel that had
    to fill a gap itself (NL/voice/receipt) rather than an exact figure.

    `use_personal_average=False` skips the personal-average fallback
    entirely and goes straight to `default_kg` -- for event-based
    categories like flights, where most days genuinely have zero, and
    averaging only over the (rare) days something WAS logged would
    wrongly assume every day includes that event.
    """
    if raw is not None:
        return _band(raw, "inferred" if inferred else "observed")

    if use_personal_average:
        dated_history = list(dated_history)
        lookback = dated_history[:WEEKDAY_LOOKBACK]

        weekday_matches = [v for d, v in lookback if d.weekday() == target_weekday][:ROLLING_WINDOW]
        if len(weekday_matches) >= WEEKDAY_MIN_SAMPLES:
            return _band(mean(weekday_matches), "personal_estimate", basis="weekday_average")

        flat = [v for _, v in dated_history[:ROLLING_WINDOW]]
        if flat:
            return _band(mean(flat), "personal_estimate", basis="rolling_average")

    return _band(default_kg, "population_default")


def estimate_entry(entry, history: Iterable, region_code: str) -> dict:
    """
    entry: the LogEntry being estimated (ORM object or anything with the
           same attribute names, plus an optional `inferred_fields` set/dict
           naming which of {"commute","food","energy","flights","shopping"}
           were filled by a gap-filling channel rather than given exactly).
    history: other LogEntry rows for this user, most-recent-date-first.
    region_code: which regional factor profile to compute against.
    """
    region = get_region(region_code)
    history = list(history)
    inferred_fields = getattr(entry, "inferred_fields", None) or set()
    target_weekday = entry.date.weekday()

    commute_history = [
        (h.date, v)
        for h in history
        if (v := _raw_commute_kg(region, h.commute_mode, h.commute_distance_km)) is not None
    ]
    food_history = [(h.date, v) for h in history if (v := _raw_food_kg(h.diet_type)) is not None]
    energy_history = [
        (h.date, v)
        for h in history
        if (v := _raw_energy_kg(region, h.energy_kwh, h.energy_level)) is not None
    ]
    shopping_history = [
        (h.date, v)
        for h in history
        if (v := _raw_shopping_kg(getattr(h, "shopping_level", None))) is not None
    ]

    defaults = population_defaults_kg_per_day(region_code)

    commute = _resolve(
        _raw_commute_kg(region, entry.commute_mode, entry.commute_distance_km),
        "commute" in inferred_fields,
        commute_history,
        defaults["commute"],
        target_weekday,
    )
    food = _resolve(
        _raw_food_kg(entry.diet_type),
        "food" in inferred_fields,
        food_history,
        defaults["food"],
        target_weekday,
    )
    energy = _resolve(
        _raw_energy_kg(region, entry.energy_kwh, entry.energy_level),
        "energy" in inferred_fields,
        energy_history,
        defaults["energy"],
        target_weekday,
    )
    flights = _resolve(
        _raw_flight_kg(getattr(entry, "flight_km", None), getattr(entry, "flight_haul", None)),
        "flights" in inferred_fields,
        [],  # no personal-average smearing -- see use_personal_average docstring
        defaults["flights"],
        target_weekday,
        use_personal_average=False,
    )
    shopping = _resolve(
        _raw_shopping_kg(getattr(entry, "shopping_level", None)),
        "shopping" in inferred_fields,
        shopping_history,
        defaults["shopping"],
        target_weekday,
    )

    categories = (commute, food, energy, flights, shopping)
    total = round(sum(c.kg_co2e for c in categories), 2)
    combined_uncertainty = math.sqrt(sum((c.kg_co2e * c.uncertainty_pct) ** 2 for c in categories))
    total_low = round(max(total - combined_uncertainty, 0), 2)
    total_high = round(total + combined_uncertainty, 2)

    return {
        "commute": commute,
        "food": food,
        "energy": energy,
        "flights": flights,
        "shopping": shopping,
        "total_kg_co2e": total,
        "total_low_kg_co2e": total_low,
        "total_high_kg_co2e": total_high,
        "region": region_code,
        "factor_version": region["version"],
    }
