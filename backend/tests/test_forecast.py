from dataclasses import dataclass
from datetime import date, timedelta

from app.forecast import forecast


@dataclass
class FakeTrendPoint:
    date: date
    total_kg_co2e: float


def test_no_data_returns_no_points():
    result = forecast([], days=7)
    assert result["points"] == []
    assert result["method"] == "insufficient_data"


def test_flat_average_used_below_three_points():
    trend = [
        FakeTrendPoint(date(2026, 1, 1), 10.0),
        FakeTrendPoint(date(2026, 1, 2), 12.0),
    ]
    result = forecast(trend, days=3)
    assert result["method"] == "flat_average"
    assert all(p.projected_kg_co2e == 11.0 for p in result["points"])


def test_upward_trend_is_extrapolated_upward():
    trend = [FakeTrendPoint(date(2026, 1, 1) + timedelta(days=i), 10.0 + i) for i in range(10)]
    result = forecast(trend, days=5)
    assert result["method"] == "linear_regression"
    projections = [p.projected_kg_co2e for p in result["points"]]
    assert projections == sorted(projections)  # still increasing
    assert projections[0] > trend[-1].total_kg_co2e


def test_forecast_dates_continue_from_last_logged_day():
    trend = [FakeTrendPoint(date(2026, 1, 1) + timedelta(days=i), 10.0) for i in range(5)]
    result = forecast(trend, days=3)
    assert [p.date for p in result["points"]] == [
        date(2026, 1, 6),
        date(2026, 1, 7),
        date(2026, 1, 8),
    ]


def test_uncertainty_band_widens_further_into_the_future():
    trend = [FakeTrendPoint(date(2026, 1, 1) + timedelta(days=i), 10.0) for i in range(5)]
    result = forecast(trend, days=5)
    bands = [p.high_kg_co2e - p.low_kg_co2e for p in result["points"]]
    assert bands == sorted(bands)  # non-decreasing
