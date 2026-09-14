"""
Flags logged days whose total footprint deviates sharply from the
user's own recent pattern.

Uses a "modified z-score" (median + MAD, not mean + stdev): with mean/
stdev, a single huge day -- a long-haul flight -- inflates the stdev
enough that the same huge day no longer looks abnormal by the metric
it should trigger. Median and MAD (median absolute deviation) are
robust to that: a handful of outliers barely move the median, so the
outliers still register as outliers. Standard technique for exactly
this "one big spike shouldn't hide itself" problem.
"""

from dataclasses import dataclass
from datetime import date as date_type
from statistics import median

MIN_DAYS_FOR_DETECTION = 5
Z_SCORE_THRESHOLD = 3.0  # conventional modified-z-score cutoff (Iglewicz & Hoaglin)
MAD_TO_STDEV = 1.4826  # scales MAD to be comparable to a normal distribution's stdev

CATEGORY_NAMES = ("commute", "food", "energy", "flights", "shopping")


@dataclass
class Anomaly:
    date: date_type
    total_kg_co2e: float
    modified_z_score: float
    direction: str  # "high" | "low"
    primary_category: str
    message: str


def _modified_z_scores(values: list[float]) -> tuple[list[float], float]:
    m = median(values)
    abs_devs = [abs(v - m) for v in values]
    mad = median(abs_devs)
    if mad == 0:
        # Happens when most values are identical (small/sparse demo data) --
        # fall back to mean absolute deviation rather than divide by zero.
        mad = sum(abs_devs) / len(abs_devs) if abs_devs else 0
    if mad == 0:
        return [0.0] * len(values), m
    return [(MAD_TO_STDEV * (v - m) / mad) for v in values], m


def detect_anomalies(trend: list) -> list[Anomaly]:
    """trend: list of LogEntryOut-shaped objects (has .date, category
    CategoryEstimate attributes, .total_kg_co2e), ascending by date."""
    if len(trend) < MIN_DAYS_FOR_DETECTION:
        return []

    totals = [t.total_kg_co2e for t in trend]
    z_scores, baseline_median = _modified_z_scores(totals)

    anomalies = []
    for entry, z in zip(trend, z_scores):
        if abs(z) < Z_SCORE_THRESHOLD:
            continue

        category_totals = {cat: getattr(entry, cat).kg_co2e for cat in CATEGORY_NAMES}
        primary = max(category_totals, key=category_totals.get)
        direction = "high" if z > 0 else "low"
        comparison = "well above" if direction == "high" else "well below"

        anomalies.append(
            Anomaly(
                date=entry.date,
                total_kg_co2e=entry.total_kg_co2e,
                modified_z_score=round(z, 2),
                direction=direction,
                primary_category=primary,
                message=(
                    f"{entry.total_kg_co2e}kg is {comparison} your typical "
                    f"~{baseline_median:.1f}kg day, mostly from {primary}."
                ),
            )
        )
    return anomalies
