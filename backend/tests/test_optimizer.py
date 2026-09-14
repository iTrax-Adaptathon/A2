from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.optimizer import optimize

REGION = "IN"


@dataclass
class FakeEntry:
    date: date
    commute_mode: Optional[str] = None
    commute_distance_km: Optional[float] = None
    diet_type: Optional[str] = None
    energy_kwh: Optional[float] = None
    energy_level: Optional[str] = None


def _history(n=5):
    return [
        FakeEntry(
            date=date(2026, 1, i + 1),
            commute_mode="car",
            commute_distance_km=15,
            diet_type="meat_heavy",
            energy_level="high",
        )
        for i in range(n)
    ]


def test_target_already_met_requires_no_actions():
    result = optimize(_history(), target_kg_per_day=1000, region_code=REGION)
    assert result["achievable"] is True
    assert result["actions"] == []
    assert result["projected_kg_per_day"] == result["baseline_kg_per_day"]


def test_ambitious_target_recommends_the_highest_impact_action_first():
    result = optimize(_history(), target_kg_per_day=1, region_code=REGION)
    assert result["actions"], "expected at least one recommended action"
    savings = [a.kg_saved_per_day for a in result["actions"]]
    assert savings == sorted(savings, reverse=True)


def test_car_heavy_history_suggests_switching_away_from_car():
    result = optimize(_history(), target_kg_per_day=1, region_code=REGION)
    commute_actions = [a for a in result["actions"] if a.lever == "commute"]
    assert commute_actions
    assert commute_actions[0].change.startswith("car")


def test_no_history_still_produces_a_sane_baseline_and_actions():
    result = optimize([], target_kg_per_day=1, region_code=REGION)
    assert result["baseline_kg_per_day"] > 0
    assert result["actions"]
