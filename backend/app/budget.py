"""
Personalized carbon budget (item 13): given a persisted daily target
(see models.Budget), computes progress -- days tracked, days under
budget, current and best streaks -- against the logged trend.

Kept as a pure function over plain data (not the ORM row directly)
so it's trivially unit-testable and swappable if a future team adds
weekly/monthly budget periods instead of just daily.
"""

from dataclasses import dataclass
from datetime import date as date_type


@dataclass
class DayStatus:
    date: date_type
    total_kg_co2e: float
    under_budget: bool


def compute_status(target_kg_per_day: float, created_date: date_type, trend: list) -> dict:
    """trend: list of LogEntryOut-shaped objects (.date, .total_kg_co2e),
    ascending by date. Only days on/after `created_date` count -- a
    budget shouldn't retroactively judge days logged before it existed."""
    tracked = [t for t in trend if t.date >= created_date]

    daily_status = [
        DayStatus(date=t.date, total_kg_co2e=t.total_kg_co2e, under_budget=t.total_kg_co2e <= target_kg_per_day)
        for t in tracked
    ]

    days_tracked = len(daily_status)
    days_under_budget = sum(1 for d in daily_status if d.under_budget)

    current_streak = 0
    for d in reversed(daily_status):
        if not d.under_budget:
            break
        current_streak += 1

    best_streak = 0
    running = 0
    for d in daily_status:
        if d.under_budget:
            running += 1
            best_streak = max(best_streak, running)
        else:
            running = 0

    return {
        "target_kg_per_day": target_kg_per_day,
        "created_date": created_date,
        "days_tracked": days_tracked,
        "days_under_budget": days_under_budget,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "daily_status": daily_status,
    }
