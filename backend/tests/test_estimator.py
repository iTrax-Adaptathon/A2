"""
Unit tests for the estimation logic in isolation -- no DB, no HTTP.
Run with: pytest (from backend/, with dev deps installed)
"""

from dataclasses import dataclass
from typing import Optional

import pytest

from app.emission_factors import (
    COMMUTE_FACTORS_KG_PER_KM,
    DIET_FACTORS_KG_PER_DAY,
    ENERGY_FACTOR_KG_PER_KWH,
    POPULATION_DEFAULT_KG_PER_DAY,
)
from app.estimator import ROLLING_WINDOW, estimate_entry


@dataclass
class FakeEntry:
    """Stand-in for a LogEntry row -- estimate_entry only reads attributes."""

    commute_mode: Optional[str] = None
    commute_distance_km: Optional[float] = None
    diet_type: Optional[str] = None
    energy_kwh: Optional[float] = None
    energy_level: Optional[str] = None


def test_fully_logged_day_uses_logged_values_directly():
    entry = FakeEntry(commute_mode="car", commute_distance_km=10, diet_type="average", energy_kwh=5)
    result = estimate_entry(entry, history=[])

    assert result["commute"].source == "logged"
    assert result["commute"].kg_co2e == round(COMMUTE_FACTORS_KG_PER_KM["car"] * 10, 2)
    assert result["food"].source == "logged"
    assert result["food"].kg_co2e == DIET_FACTORS_KG_PER_DAY["average"]
    assert result["energy"].source == "logged"
    assert result["energy"].kg_co2e == round(5 * ENERGY_FACTOR_KG_PER_KWH, 2)
    assert result["total_kg_co2e"] == round(
        result["commute"].kg_co2e + result["food"].kg_co2e + result["energy"].kg_co2e, 2
    )


def test_missing_category_with_no_history_falls_back_to_population_default():
    entry = FakeEntry(commute_mode="bus", commute_distance_km=5)  # food/energy blank
    result = estimate_entry(entry, history=[])

    assert result["food"].source == "default"
    assert result["food"].kg_co2e == round(POPULATION_DEFAULT_KG_PER_DAY["food"], 2)
    assert result["energy"].source == "default"
    assert result["energy"].kg_co2e == round(POPULATION_DEFAULT_KG_PER_DAY["energy"], 2)


def test_missing_category_with_history_falls_back_to_personal_average():
    entry = FakeEntry(commute_mode="bus", commute_distance_km=5)  # diet blank
    history = [
        FakeEntry(diet_type="vegan"),  # 2.89
        FakeEntry(diet_type="meat_heavy"),  # 7.19
    ]
    result = estimate_entry(entry, history=history)

    expected = round(
        (DIET_FACTORS_KG_PER_DAY["vegan"] + DIET_FACTORS_KG_PER_DAY["meat_heavy"]) / 2, 2
    )
    assert result["food"].source == "estimated"
    assert result["food"].kg_co2e == expected


def test_rolling_window_only_considers_most_recent_n_entries():
    entry = FakeEntry(commute_mode="bus", commute_distance_km=5)
    # ROLLING_WINDOW entries of "average" (5.63) followed by older "vegan" (2.89)
    # entries that should be excluded from the average.
    recent = [FakeEntry(diet_type="average") for _ in range(ROLLING_WINDOW)]
    older = [FakeEntry(diet_type="vegan") for _ in range(5)]
    history = recent + older  # most-recent-first ordering

    result = estimate_entry(entry, history=history)

    assert result["food"].kg_co2e == DIET_FACTORS_KG_PER_DAY["average"]


def test_entirely_blank_day_still_produces_a_total():
    entry = FakeEntry()
    result = estimate_entry(entry, history=[])

    assert result["commute"].source == "default"
    assert result["food"].source == "default"
    assert result["energy"].source == "default"
    assert result["total_kg_co2e"] > 0


@pytest.mark.parametrize("mode", list(COMMUTE_FACTORS_KG_PER_KM.keys()))
def test_every_commute_mode_is_computable(mode):
    entry = FakeEntry(commute_mode=mode, commute_distance_km=10)
    result = estimate_entry(entry, history=[])
    assert result["commute"].kg_co2e == round(COMMUTE_FACTORS_KG_PER_KM[mode] * 10, 2)
