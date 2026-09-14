"""
"AI Carbon Analyst" (item 15): a rule-based engine that reads the
trend, forecast, and optimizer outputs and narrates them as plain-
language insights -- the same role an LLM-backed analyst would play,
without needing an external API key wired into this Sprint 1 build.

Deliberately isolated (takes plain data in, returns plain Insight
objects out) so swapping the rule engine below for a real LLM call
(e.g. handing this same context to the Claude API and asking it to
narrate) is a contained Sprint 2 change -- nothing else in the app
needs to know the difference.
"""

from statistics import mean

from .emission_factors import get_region
from .forecast import forecast as run_forecast
from .optimizer import optimize as run_optimize

LOW_CERTAINTY_SOURCES = {"personal_estimate", "population_default"}


def _category_sources(trend) -> list[str]:
    # Flights excluded deliberately: its "population_default" is 0kg
    # (no evidence of flying = assume no flight), which is a near-certain
    # assumption, not a guessed footprint the way a nonzero commute/food/
    # energy/shopping default is -- including it would make normal days
    # look artificially "low certainty".
    sources = []
    for entry in trend:
        sources += [entry.commute.source, entry.food.source, entry.energy.source, entry.shopping.source]
    return sources


def generate_insights(trend, raw_history: list, region_code: str) -> list[dict]:
    insights: list[dict] = []

    if not trend:
        return [
            {
                "type": "onboarding",
                "headline": "No data yet",
                "detail": "Log a day (form, natural language, voice, or a receipt) to unlock analysis.",
                "severity": "info",
            }
        ]

    totals = [t.total_kg_co2e for t in trend]

    # --- trend direction ---
    if len(trend) >= 4:
        window = min(7, len(trend) // 2)
        recent = mean(totals[-window:])
        prior = mean(totals[-2 * window : -window])
        if prior > 0:
            change_pct = (recent - prior) / prior * 100
            if change_pct >= 10:
                insights.append(
                    {
                        "type": "trend",
                        "headline": f"Footprint up {change_pct:.0f}% recently",
                        "detail": f"Your last {window} days averaged {recent:.1f}kg/day vs {prior:.1f}kg/day the {window} before that.",
                        "severity": "warning",
                    }
                )
            elif change_pct <= -10:
                insights.append(
                    {
                        "type": "trend",
                        "headline": f"Footprint down {abs(change_pct):.0f}% recently",
                        "detail": f"Your last {window} days averaged {recent:.1f}kg/day vs {prior:.1f}kg/day the {window} before that. Keep it up.",
                        "severity": "positive",
                    }
                )

    # --- biggest contributor ---
    category_totals = {
        "commute": round(sum(t.commute.kg_co2e for t in trend), 2),
        "food": round(sum(t.food.kg_co2e for t in trend), 2),
        "energy": round(sum(t.energy.kg_co2e for t in trend), 2),
        "flights": round(sum(t.flights.kg_co2e for t in trend), 2),
        "shopping": round(sum(t.shopping.kg_co2e for t in trend), 2),
    }
    biggest = max(category_totals, key=category_totals.get)
    insights.append(
        {
            "type": "breakdown",
            "headline": f"{biggest.capitalize()} is your biggest contributor",
            "detail": f"{biggest.capitalize()} accounts for {category_totals[biggest]}kg of your {round(sum(totals),2)}kg logged total.",
            "severity": "info",
        }
    )

    # --- data quality ---
    sources = _category_sources(trend)
    low_certainty_ratio = sum(1 for s in sources if s in LOW_CERTAINTY_SOURCES) / len(sources)
    if low_certainty_ratio > 0.5:
        insights.append(
            {
                "type": "data_quality",
                "headline": "Most of your footprint is inferred, not logged",
                "detail": f"{low_certainty_ratio*100:.0f}% of category values are personal-average or default fallbacks. Log exact numbers when you can for tighter estimates.",
                "severity": "warning",
            }
        )
    else:
        insights.append(
            {
                "type": "data_quality",
                "headline": "Good logging coverage",
                "detail": f"{100-low_certainty_ratio*100:.0f}% of your category values are directly observed or inferred from what you logged, not guessed.",
                "severity": "positive",
            }
        )

    # --- flights: called out separately since a single trip can dwarf
    # weeks of daily habits, and it's the one category the optimizer
    # can't offer a lever for ---
    flight_total = category_totals["flights"]
    if flight_total > 0:
        insights.append(
            {
                "type": "flights",
                "headline": f"Flights contributed {flight_total}kg this period",
                "detail": "Flights aren't part of the optimizer's levers (a trip already happened) but are counted in your totals -- they're often the single largest line item in a personal footprint.",
                "severity": "warning" if flight_total > sum(category_totals.values()) * 0.3 else "info",
            }
        )

    # --- forecast-based ---
    fc = run_forecast(trend, days=7)
    if fc["points"]:
        avg_recent = mean(totals[-min(7, len(totals)) :])
        avg_projected = mean(p.projected_kg_co2e for p in fc["points"])
        if avg_projected > avg_recent * 1.1:
            insights.append(
                {
                    "type": "forecast",
                    "headline": "Trajectory is rising",
                    "detail": f"At this rate, the next 7 days project to ~{avg_projected:.1f}kg/day on average, up from ~{avg_recent:.1f}kg/day recently.",
                    "severity": "warning",
                }
            )

    # --- optimizer teaser: a quick win toward a modest 20%-lower target ---
    baseline_guess = mean(totals[-min(14, len(totals)) :])
    opt = run_optimize(raw_history, target_kg_per_day=round(baseline_guess * 0.8, 2), region_code=region_code)
    if opt["actions"]:
        top = opt["actions"][0]
        insights.append(
            {
                "type": "recommendation",
                "headline": f"Quick win: {top.change}",
                "detail": f"{top.rationale} Estimated saving: {top.kg_saved_per_day}kg/day.",
                "severity": "positive",
            }
        )

    # --- region context ---
    region = get_region(region_code)
    insights.append(
        {
            "type": "region",
            "headline": f"Using {region['label']} factors (v{region['version']})",
            "detail": "Switch region in Settings if you split time across countries -- estimates recompute automatically.",
            "severity": "info",
        }
    )

    return insights
