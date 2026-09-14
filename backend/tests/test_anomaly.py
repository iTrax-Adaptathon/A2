from dataclasses import dataclass
from datetime import date, timedelta

from app.anomaly import MIN_DAYS_FOR_DETECTION, detect_anomalies


@dataclass
class FakeCategory:
    kg_co2e: float


@dataclass
class FakeTrendPoint:
    date: date
    total_kg_co2e: float
    commute: FakeCategory
    food: FakeCategory
    energy: FakeCategory
    flights: FakeCategory
    shopping: FakeCategory


def _normal_day(d, total=10.0):
    return FakeTrendPoint(
        date=d,
        total_kg_co2e=total,
        commute=FakeCategory(total * 0.3),
        food=FakeCategory(total * 0.5),
        energy=FakeCategory(total * 0.2),
        flights=FakeCategory(0.0),
        shopping=FakeCategory(0.0),
    )


def _flight_day(d, flight_kg=660.0, baseline=10.0):
    return FakeTrendPoint(
        date=d,
        total_kg_co2e=baseline + flight_kg,
        commute=FakeCategory(baseline * 0.3),
        food=FakeCategory(baseline * 0.5),
        energy=FakeCategory(baseline * 0.2),
        flights=FakeCategory(flight_kg),
        shopping=FakeCategory(0.0),
    )


def _dates(n, start=date(2026, 1, 1)):
    return [start + timedelta(days=i) for i in range(n)]


def test_too_few_days_returns_no_anomalies():
    trend = [_normal_day(d) for d in _dates(MIN_DAYS_FOR_DETECTION - 1)]
    assert detect_anomalies(trend) == []


def test_all_identical_days_have_no_anomalies():
    trend = [_normal_day(d) for d in _dates(10)]
    assert detect_anomalies(trend) == []


def test_a_flight_day_is_flagged_high_with_flights_as_primary_category():
    dates = _dates(10)
    trend = [_normal_day(d) for d in dates]
    trend[5] = _flight_day(dates[5])

    anomalies = detect_anomalies(trend)
    assert len(anomalies) == 1
    assert anomalies[0].date == dates[5]
    assert anomalies[0].direction == "high"
    assert anomalies[0].primary_category == "flights"
    assert "flights" in anomalies[0].message


def test_a_near_zero_day_is_flagged_low():
    dates = _dates(10)
    trend = [_normal_day(d) for d in dates]
    trend[3] = _normal_day(dates[3], total=0.1)

    anomalies = detect_anomalies(trend)
    assert any(a.date == dates[3] and a.direction == "low" for a in anomalies)


def test_normal_variation_does_not_trigger_false_positives():
    dates = _dates(12)
    # Mild day-to-day variation, nothing dramatic.
    trend = [_normal_day(d, total=10.0 + (i % 3)) for i, d in enumerate(dates)]
    assert detect_anomalies(trend) == []
