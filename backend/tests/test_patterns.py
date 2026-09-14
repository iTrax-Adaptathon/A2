from dataclasses import dataclass
from datetime import date, timedelta

from app.patterns import MIN_DAYS_FOR_PATTERNS, weekday_breakdown


@dataclass
class FakeTrendPoint:
    date: date
    total_kg_co2e: float


def test_too_few_days_reports_not_enough_data():
    trend = [FakeTrendPoint(date(2026, 1, 1) + timedelta(days=i), 10.0) for i in range(MIN_DAYS_FOR_PATTERNS - 1)]
    result = weekday_breakdown(trend)
    assert result["enough_data"] is False
    assert result["weekdays"] == []


def test_identifies_highest_and_lowest_weekday():
    # 2026-01-05 is a Monday (see estimator tests' A_MONDAY anchor).
    monday = date(2026, 1, 5)
    trend = []
    for week in range(3):
        trend.append(FakeTrendPoint(monday + timedelta(weeks=week), 20.0))  # Monday: high
        trend.append(FakeTrendPoint(monday + timedelta(weeks=week, days=6), 2.0))  # Sunday: low
        trend.append(FakeTrendPoint(monday + timedelta(weeks=week, days=3), 10.0))  # Thursday: mid

    result = weekday_breakdown(trend)
    assert result["enough_data"] is True
    assert result["highest"].label == "Monday"
    assert result["highest"].average_kg_co2e == 20.0
    assert result["lowest"].label == "Sunday"
    assert result["lowest"].average_kg_co2e == 2.0


def test_days_sampled_reflects_occurrence_count():
    monday = date(2026, 1, 5)
    trend = [FakeTrendPoint(monday, 10.0), FakeTrendPoint(monday + timedelta(weeks=1), 12.0)]
    # Pad to reach the minimum.
    trend += [FakeTrendPoint(monday + timedelta(days=1), 5.0), FakeTrendPoint(monday + timedelta(days=2), 5.0)]

    result = weekday_breakdown(trend)
    monday_bucket = next(w for w in result["weekdays"] if w.label == "Monday")
    assert monday_bucket.days_sampled == 2
    assert monday_bucket.average_kg_co2e == 11.0
