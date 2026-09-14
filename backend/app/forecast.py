
from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta


@dataclass
class ForecastPoint:
    date: date_type
    projected_kg_co2e: float
    low_kg_co2e: float
    high_kg_co2e: float


def _least_squares(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0, mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    intercept = mean_y - slope * mean_x
    return slope, intercept


def forecast(trend: list, days: int = 7) -> dict:
    """
    trend: list of objects with `.date` and `.total_kg_co2e`, sorted
           ascending by date (as SummaryOut.trend already is).
    """
    if not trend:
        return {"method": "insufficient_data", "basis_days": 0, "points": []}

    last_date = trend[-1].date
    totals = [t.total_kg_co2e for t in trend]

    if len(trend) < 3:
        avg = sum(totals) / len(totals)
        method = "flat_average"
        slope, intercept = 0.0, avg
    else:
        xs = list(range(len(trend)))
        ys = totals
        slope, intercept = _least_squares(xs, ys)
        method = "linear_regression"

    points = []
    n = len(trend)
    for i in range(1, days + 1):
        x = n - 1 + i
        projected = max(intercept + slope * x, 0)
        # Widen the band the further out we project.
        pct = min(0.15 + 0.05 * i, 0.6)
        delta = projected * pct
        points.append(
            ForecastPoint(
                date=last_date + timedelta(days=i),
                projected_kg_co2e=round(projected, 2),
                low_kg_co2e=round(max(projected - delta, 0), 2),
                high_kg_co2e=round(projected + delta, 2),
            )
        )

    return {"method": method, "basis_days": len(trend), "points": points}
