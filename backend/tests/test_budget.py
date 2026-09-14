from dataclasses import dataclass
from datetime import date, timedelta

from app.budget import compute_status


@dataclass
class FakeTrendPoint:
    date: date
    total_kg_co2e: float


def _dates(n, start=date(2026, 1, 1)):
    return [start + timedelta(days=i) for i in range(n)]


def test_no_tracked_days_before_budget_was_created():
    d = _dates(3)
    trend = [FakeTrendPoint(d[0], 5.0), FakeTrendPoint(d[1], 5.0)]
    result = compute_status(target_kg_per_day=10.0, created_date=d[2], trend=trend)
    assert result["days_tracked"] == 0
    assert result["current_streak"] == 0
    assert result["best_streak"] == 0


def test_days_before_created_date_are_excluded():
    d = _dates(4)
    trend = [
        FakeTrendPoint(d[0], 100.0),  # before budget -- should not count as "over"
        FakeTrendPoint(d[1], 5.0),
        FakeTrendPoint(d[2], 5.0),
    ]
    result = compute_status(target_kg_per_day=10.0, created_date=d[1], trend=trend)
    assert result["days_tracked"] == 2
    assert result["days_under_budget"] == 2


def test_current_streak_counts_back_from_most_recent_under_budget_run():
    d = _dates(6)
    totals = [5.0, 15.0, 5.0, 5.0, 5.0, 15.0]  # over, under, under, under, over (reading forward)
    trend = [FakeTrendPoint(d[i], totals[i]) for i in range(6)]
    result = compute_status(target_kg_per_day=10.0, created_date=d[0], trend=trend)

    # Most recent day (index 5) is over budget -> current streak is 0.
    assert result["current_streak"] == 0
    # Longest under-budget run is indices 2-4 (3 in a row).
    assert result["best_streak"] == 3


def test_current_streak_is_nonzero_when_trailing_days_are_under_budget():
    d = _dates(4)
    trend = [
        FakeTrendPoint(d[0], 20.0),  # over
        FakeTrendPoint(d[1], 5.0),  # under
        FakeTrendPoint(d[2], 5.0),  # under
        FakeTrendPoint(d[3], 5.0),  # under
    ]
    result = compute_status(target_kg_per_day=10.0, created_date=d[0], trend=trend)
    assert result["current_streak"] == 3
    assert result["daily_status"][0].under_budget is False
    assert result["daily_status"][-1].under_budget is True


def test_exactly_at_target_counts_as_under_budget():
    d = _dates(1)
    trend = [FakeTrendPoint(d[0], 10.0)]
    result = compute_status(target_kg_per_day=10.0, created_date=d[0], trend=trend)
    assert result["days_under_budget"] == 1
