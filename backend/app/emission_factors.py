"""
Emission factor reference data.

All factors are approximate, India-weighted averages intended for a
relative "which choices matter most" comparison, NOT for regulatory or
scientific carbon accounting. Sources: typical figures used by
Our World in Data / DEFRA-style calculators, rounded for readability.

This file is deliberately isolated from the estimation logic (see
estimator.py) so a future team can swap in a better model, per-country
factors, or a live emissions API without touching anything else.
"""

# kg CO2e per passenger-km
COMMUTE_FACTORS_KG_PER_KM = {
    "car": 0.192,       # petrol car, solo driver
    "bike": 0.103,      # motorbike/scooter
    "bus": 0.105,
    "train": 0.041,     # metro/rail
    "cycle": 0.0,
    "walk": 0.0,
    "wfh": 0.0,          # no commute
}

# kg CO2e per day, by overall diet pattern
DIET_FACTORS_KG_PER_DAY = {
    "meat_heavy": 7.19,
    "average": 5.63,
    "vegetarian": 3.81,
    "vegan": 2.89,
}

# kg CO2e per kWh (approx. India grid average)
ENERGY_FACTOR_KG_PER_KWH = 0.82

# Fallback kWh/day per person when a user logs a qualitative level
# instead of a meter reading.
ENERGY_LEVEL_KWH = {
    "low": 3.0,
    "medium": 8.0,
    "high": 15.0,
}

# Population-average fallback (kg CO2e/day) used only when a brand new
# user has zero history for a category yet, so the very first log entry
# still gets a sensible total.
POPULATION_DEFAULT_KG_PER_DAY = {
    "commute": 4.5,
    "food": DIET_FACTORS_KG_PER_DAY["average"],
    "energy": ENERGY_LEVEL_KWH["medium"] * ENERGY_FACTOR_KG_PER_KWH,
}
