"""
Unit tests for the estimation logic in isolation -- no DB, no HTTP.
Run with: pytest (from backend/, with dev deps installed)
"""

from dataclasses import dataclass, field
from typing import Optional

import pytest

from app.emission_factors import (
    DIET_FACTORS_KG_PER_DAY,
    FLIGHT_FACTORS_KG_PER_KM,
    SHOPPING_LEVEL_KG_PER_DAY,
    get_region,
    population_defaults_kg_per_day,
)
from app.estimator import ROLLING_WINDOW, estimate_entry

REGION = "IN"


@dataclass
class FakeEntry:
    """Stand-in for a LogEntry row -- estimate_entry only reads attributes."""

    commute_mode: Optional[str] = None
    commute_distance_km: Optional[float] = None
    diet_type: Optional[str] = None
    energy_kwh: Optional[float] = None
    energy_level: Optional[str] = None
    flight_km: Optional[float] = None
    flight_haul: Optional[str] = None
    shopping_level: Optional[str] = None
    inferred_fields: set = field(default_factory=set)


def _sum_categories(result):
    return round(
        result["commute"].kg_co2e
        + result["food"].kg_co2e
        + result["energy"].kg_co2e
        + result["flights"].kg_co2e
        + result["shopping"].kg_co2e,
        2,
    )


def test_fully_logged_day_uses_observed_values_directly():
    entry = FakeEntry(
        commute_mode="car",
        commute_distance_km=10,
        diet_type="average",
        energy_kwh=5,
        flight_km=1000,
        flight_haul="short",
        shopping_level="medium",
    )
    result = estimate_entry(entry, history=[], region_code=REGION)
    region = get_region(REGION)

    assert result["commute"].source == "observed"
    assert result["commute"].kg_co2e == round(region["commute_kg_per_km"]["car"] * 10, 2)
    assert result["food"].source == "observed"
    assert result["food"].kg_co2e == DIET_FACTORS_KG_PER_DAY["average"]
    assert result["energy"].source == "observed"
    assert result["energy"].kg_co2e == round(5 * region["energy_kg_per_kwh"], 2)
    assert result["flights"].source == "observed"
    assert result["flights"].kg_co2e == round(FLIGHT_FACTORS_KG_PER_KM["short"] * 1000, 2)
    assert result["shopping"].source == "observed"
    assert result["shopping"].kg_co2e == SHOPPING_LEVEL_KG_PER_DAY["medium"]
    assert result["total_kg_co2e"] == _sum_categories(result)
    assert result["region"] == REGION
    assert result["factor_version"] == region["version"]


def test_inferred_field_is_tagged_and_carries_more_uncertainty_than_observed():
    entry = FakeEntry(commute_mode="car", commute_distance_km=10, inferred_fields={"commute"})
    result = estimate_entry(entry, history=[], region_code=REGION)

    assert result["commute"].source == "inferred"
    assert result["commute"].uncertainty_pct > 0.05  # wider band than "observed"


def test_missing_category_with_no_history_falls_back_to_population_default():
    entry = FakeEntry(commute_mode="bus", commute_distance_km=5)  # food/energy/shopping blank
    result = estimate_entry(entry, history=[], region_code=REGION)
    defaults = population_defaults_kg_per_day(REGION)

    assert result["food"].source == "population_default"
    assert result["food"].kg_co2e == round(defaults["food"], 2)
    assert result["energy"].source == "population_default"
    assert result["energy"].kg_co2e == round(defaults["energy"], 2)
    assert result["shopping"].source == "population_default"
    assert result["shopping"].kg_co2e == round(defaults["shopping"], 2)


def test_missing_category_with_history_falls_back_to_personal_average():
    entry = FakeEntry(commute_mode="bus", commute_distance_km=5)  # diet blank
    history = [
        FakeEntry(diet_type="vegan"),  # 2.89
        FakeEntry(diet_type="meat_heavy"),  # 7.19
    ]
    result = estimate_entry(entry, history=history, region_code=REGION)

    expected = round(
        (DIET_FACTORS_KG_PER_DAY["vegan"] + DIET_FACTORS_KG_PER_DAY["meat_heavy"]) / 2, 2
    )
    assert result["food"].source == "personal_estimate"
    assert result["food"].kg_co2e == expected


def test_flights_default_to_zero_even_with_flight_history_not_a_smeared_average():
    """Flights are event-based: if the user flew on some past days but not
    today, today's default should be 0 -- NOT the average of the days they
    did fly, which would wrongly assume every day includes a flight."""
    entry = FakeEntry(commute_mode="bus", commute_distance_km=5)  # no flight today
    history = [
        FakeEntry(flight_km=6000, flight_haul="long"),  # a real past flight
        FakeEntry(flight_km=6000, flight_haul="long"),
    ]
    result = estimate_entry(entry, history=history, region_code=REGION)

    assert result["flights"].source == "population_default"
    assert result["flights"].kg_co2e == 0.0


def test_shopping_uses_normal_personal_average_unlike_flights():
    entry = FakeEntry(commute_mode="bus", commute_distance_km=5)  # shopping blank today
    history = [
        FakeEntry(shopping_level="high"),
        FakeEntry(shopping_level="low"),
    ]
    result = estimate_entry(entry, history=history, region_code=REGION)

    expected = round((SHOPPING_LEVEL_KG_PER_DAY["high"] + SHOPPING_LEVEL_KG_PER_DAY["low"]) / 2, 2)
    assert result["shopping"].source == "personal_estimate"
    assert result["shopping"].kg_co2e == expected


def test_rolling_window_only_considers_most_recent_n_entries():
    entry = FakeEntry(commute_mode="bus", commute_distance_km=5)
    recent = [FakeEntry(diet_type="average") for _ in range(ROLLING_WINDOW)]
    older = [FakeEntry(diet_type="vegan") for _ in range(5)]
    history = recent + older  # most-recent-first ordering

    result = estimate_entry(entry, history=history, region_code=REGION)

    assert result["food"].kg_co2e == DIET_FACTORS_KG_PER_DAY["average"]


def test_entirely_blank_day_still_produces_a_total_with_a_range():
    entry = FakeEntry()
    result = estimate_entry(entry, history=[], region_code=REGION)

    assert result["commute"].source == "population_default"
    assert result["food"].source == "population_default"
    assert result["energy"].source == "population_default"
    assert result["flights"].source == "population_default"
    assert result["flights"].kg_co2e == 0.0
    assert result["shopping"].source == "population_default"
    assert result["total_kg_co2e"] > 0
    assert result["total_low_kg_co2e"] < result["total_kg_co2e"] < result["total_high_kg_co2e"]
    assert result["total_kg_co2e"] == _sum_categories(result)


def test_more_observed_categories_narrows_the_total_uncertainty_band():
    all_observed = FakeEntry(commute_mode="car", commute_distance_km=10, diet_type="average", energy_kwh=5)
    all_default = FakeEntry()

    observed_result = estimate_entry(all_observed, history=[], region_code=REGION)
    default_result = estimate_entry(all_default, history=[], region_code=REGION)

    observed_band = observed_result["total_high_kg_co2e"] - observed_result["total_low_kg_co2e"]
    default_band = default_result["total_high_kg_co2e"] - default_result["total_low_kg_co2e"]
    assert observed_band < default_band


@pytest.mark.parametrize("region_code", ["IN", "US", "EU", "GLOBAL"])
def test_every_region_is_computable(region_code):
    entry = FakeEntry(commute_mode="car", commute_distance_km=10, diet_type="average", energy_kwh=5)
    result = estimate_entry(entry, history=[], region_code=region_code)
    assert result["total_kg_co2e"] > 0
    assert result["region"] == region_code


@pytest.mark.parametrize("mode", list(get_region(REGION)["commute_kg_per_km"].keys()))
def test_every_commute_mode_is_computable(mode):
    entry = FakeEntry(commute_mode=mode, commute_distance_km=10)
    result = estimate_entry(entry, history=[], region_code=REGION)
    region = get_region(REGION)
    assert result["commute"].kg_co2e == round(region["commute_kg_per_km"][mode] * 10, 2)


@pytest.mark.parametrize("haul", list(FLIGHT_FACTORS_KG_PER_KM.keys()))
def test_every_flight_haul_is_computable(haul):
    entry = FakeEntry(flight_km=2000, flight_haul=haul)
    result = estimate_entry(entry, history=[], region_code=REGION)
    assert result["flights"].kg_co2e == round(FLIGHT_FACTORS_KG_PER_KM[haul] * 2000, 2)
