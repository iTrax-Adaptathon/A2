"""
Versioned, regional emission-factor registry.

All factors are approximate, rounded for readability, intended for a
*relative* "which choices matter most" comparison rather than
regulatory-grade carbon accounting. Sources: typical figures used by
Our World in Data / DEFRA / national-grid-average style calculators.

Why "versioned": every computed estimate records which region + factor
version produced it (see estimator.py / schemas.py). If the numbers in
a region below are ever revised, bump its `version` string rather than
editing in place -- old estimates stay reproducible/explainable instead
of silently drifting.
"""

DEFAULT_REGION = "IN"

REGIONS = {
    "IN": {
        "label": "India",
        "version": "2026.1",
        "commute_kg_per_km": {
            "car": 0.192,
            "bike": 0.103,
            "bus": 0.105,
            "train": 0.041,
            "cycle": 0.0,
            "walk": 0.0,
            "wfh": 0.0,
        },
        "energy_kg_per_kwh": 0.82,
    },
    "US": {
        "label": "United States",
        "version": "2026.1",
        "commute_kg_per_km": {
            "car": 0.24,
            "bike": 0.13,
            "bus": 0.15,
            "train": 0.06,
            "cycle": 0.0,
            "walk": 0.0,
            "wfh": 0.0,
        },
        "energy_kg_per_kwh": 0.42,
    },
    "EU": {
        "label": "European Union",
        "version": "2026.1",
        "commute_kg_per_km": {
            "car": 0.17,
            "bike": 0.09,
            "bus": 0.09,
            "train": 0.035,
            "cycle": 0.0,
            "walk": 0.0,
            "wfh": 0.0,
        },
        "energy_kg_per_kwh": 0.23,
    },
    "GLOBAL": {
        "label": "Global average",
        "version": "2026.1",
        "commute_kg_per_km": {
            "car": 0.19,
            "bike": 0.10,
            "bus": 0.10,
            "train": 0.04,
            "cycle": 0.0,
            "walk": 0.0,
            "wfh": 0.0,
        },
        "energy_kg_per_kwh": 0.48,
    },
}

# Diet and household-energy-level assumptions are treated as
# region-independent in this model (they describe consumption
# patterns, not grid/vehicle mix) -- only the conversion factor above
# (kg per kWh, kg per km) varies by region.
DIET_FACTORS_KG_PER_DAY = {
    "meat_heavy": 7.19,
    "average": 5.63,
    "vegetarian": 3.81,
    "vegan": 2.89,
}

ENERGY_LEVEL_KWH = {
    "low": 3.0,
    "medium": 8.0,
    "high": 15.0,
}


def list_regions():
    return [
        {"code": code, "label": r["label"], "version": r["version"]}
        for code, r in REGIONS.items()
    ]


def get_region(code: str) -> dict:
    if code not in REGIONS:
        raise KeyError(f"Unknown region '{code}'. Valid: {list(REGIONS)}")
    return REGIONS[code]


def population_defaults_kg_per_day(region_code: str) -> dict:
    """Fallback used only when a user has zero personal history in a
    category yet, so the very first log entry still gets a sensible
    number instead of a misleading zero."""
    region = get_region(region_code)
    return {
        "commute": round(region["commute_kg_per_km"]["car"] * 12, 2),  # ~12km typical one-way commute
        "food": DIET_FACTORS_KG_PER_DAY["average"],
        "energy": round(ENERGY_LEVEL_KWH["medium"] * region["energy_kg_per_kwh"], 2),
    }
