"""
Breaks the logged trend down by day of week to surface recurring
habits (e.g. "you drive more on Mondays"). Just a per-weekday average
for now -- it's also the same grouping the estimator's weekday-aware
reconstruction uses internally (see estimator.py's WEEKDAY_LOOKBACK).
"""

from dataclasses import dataclass
from statistics import mean

WEEKDAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MIN_DAYS_FOR_PATTERNS = 4


@dataclass
class WeekdayAverage:
    weekday: int  # 0=Monday .. 6=Sunday
    label: str
    average_kg_co2e: float
    days_sampled: int


def weekday_breakdown(trend: list) -> dict:
    """trend: list of LogEntryOut-shaped objects with .date and
    .total_kg_co2e. Returns per-weekday averages plus the highest/
    lowest weekday, or an empty/low-confidence result under
    MIN_DAYS_FOR_PATTERNS."""
    if len(trend) < MIN_DAYS_FOR_PATTERNS:
        return {"enough_data": False, "weekdays": [], "highest": None, "lowest": None}

    buckets: dict[int, list[float]] = {i: [] for i in range(7)}
    for entry in trend:
        buckets[entry.date.weekday()].append(entry.total_kg_co2e)

    weekdays = [
        WeekdayAverage(
            weekday=i,
            label=WEEKDAY_LABELS[i],
            average_kg_co2e=round(mean(values), 2),
            days_sampled=len(values),
        )
        for i, values in buckets.items()
        if values
    ]

    sampled = [w for w in weekdays if w.days_sampled >= 1]
    highest = max(sampled, key=lambda w: w.average_kg_co2e) if sampled else None
    lowest = min(sampled, key=lambda w: w.average_kg_co2e) if sampled else None

    return {
        "enough_data": True,
        "weekdays": sorted(weekdays, key=lambda w: w.weekday),
        "highest": highest,
        "lowest": lowest,
    }
