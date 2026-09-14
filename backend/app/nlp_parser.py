"""
Rule-based text -> structured-log parser. Powers three of the four
logging channels (item 1, multi-modal logging):

  - natural language: user types a sentence, this parses it directly.
  - voice: the browser transcribes speech to text client-side (Web
    Speech API, no backend cost), then sends the transcript here --
    same code path as natural language.
  - receipt: the browser OCRs an uploaded image client-side
    (tesseract.js), then sends the extracted text here with
    channel="receipt", which additionally checks receipt-specific
    patterns (fuel litres, electricity units, grocery item keywords)
    before falling through to the general parser.

No external LLM call -- deliberately kept as regex/keyword heuristics
so it needs no API key and is fast enough to run per-keystroke-ish in
a demo. Swapping this module for a real LLM-based extractor (e.g. the
Claude API) is a natural Sprint 2 upgrade; the rest of the app only
depends on the ParsedResult shape, not on how it's produced.
"""

import re
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import timedelta

MILES_TO_KM = 1.60934
AVG_CAR_KM_PER_LITRE = 15.0  # rough average, used only to interpret fuel-receipt litres

COMMUTE_KEYWORDS = {
    # Order matters: _find_keyword returns the first bucket that matches,
    # so "motorbike"/"scooter" must be checked before the bare "bike"
    # substring in the cycle bucket below.
    "bike": ["motorbike", "scooter", "motorcycle"],
    "car": ["car", "drove", "driving", "drive"],
    "bus": ["bus"],
    "train": ["train", "metro", "subway", "rail"],
    "cycle": ["cycled", "cycle", "bicycle", "bike"],
    "walk": ["walked", "walk", "on foot", "foot"],
    "wfh": ["work from home", "wfh", "worked from home", "stayed home", "didn't commute", "no commute"],
}

DIET_KEYWORDS = {
    "vegan": ["vegan"],
    "vegetarian": ["vegetarian", "veggie", "no meat"],
    "meat_heavy": ["meat", "chicken", "beef", "mutton", "pork", "fish", "non-veg", "nonveg", "steak"],
    "average": ["average diet", "mixed diet", "normal meals"],
}

RECEIPT_MEAT_ITEMS = ["chicken", "mutton", "beef", "fish", "egg", "pork", "prawn"]
RECEIPT_VEG_ITEMS = ["paneer", "tofu", "vegetable", "veg ", "salad", "fruit"]

ENERGY_LEVEL_KEYWORDS = {
    "low": ["low energy", "low usage", "barely used", "light usage"],
    "high": ["high energy", "ac all day", "heater all day", "heavy usage", "high usage"],
    "medium": ["normal usage", "medium usage", "average energy"],
}


@dataclass
class ParsedResult:
    date: date_type
    commute_mode: str | None = None
    commute_distance_km: float | None = None
    diet_type: str | None = None
    energy_kwh: float | None = None
    energy_level: str | None = None
    inferred_fields: set = field(default_factory=set)
    explanations: list = field(default_factory=list)


def _find_keyword(text: str, keyword_map: dict) -> str | None:
    for key, words in keyword_map.items():
        for w in words:
            if w and w in text:
                return key
    return None


def _find_distance_km(text: str) -> float | None:
    km_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:km|kilometers?|kilometres?)\b", text)
    if km_match:
        return float(km_match.group(1))
    mi_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mi|miles?)\b", text)
    if mi_match:
        return round(float(mi_match.group(1)) * MILES_TO_KM, 1)
    return None


def _find_energy_kwh(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kwh|units?)\b", text)
    return float(match.group(1)) if match else None


def parse_text(text: str, channel: str = "natural_language", today: date_type | None = None) -> ParsedResult:
    today = today or date_type.today()
    lower = text.lower()

    result = ParsedResult(date=today)

    if "yesterday" in lower:
        result.date = today - timedelta(days=1)

    # --- commute ---
    mode = _find_keyword(lower, COMMUTE_KEYWORDS)
    if mode:
        result.commute_mode = mode
        distance = _find_distance_km(lower)
        if distance is not None:
            result.commute_distance_km = distance
            result.explanations.append(f"Commute: {mode}, {distance}km (stated)")
        elif mode != "wfh":
            # Mode named but no distance -- fill a typical assumption and
            # flag it as inferred rather than observed.
            result.commute_distance_km = 10.0
            result.inferred_fields.add("commute")
            result.explanations.append(
                f"Commute: detected '{mode}' but no distance -- assumed a typical 10km"
            )
        else:
            result.commute_distance_km = 0.0
            result.explanations.append("Commute: work from home (0km)")

    # --- receipt-specific: fuel litres -> implied driving distance ---
    if channel == "receipt":
        fuel_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:l|ltr|litre|liter)s?\b", lower)
        if fuel_match and result.commute_mode is None:
            litres = float(fuel_match.group(1))
            result.commute_mode = "car"
            result.commute_distance_km = round(litres * AVG_CAR_KM_PER_LITRE, 1)
            result.inferred_fields.add("commute")
            result.explanations.append(
                f"Receipt: {litres}L fuel detected -- estimated ~{result.commute_distance_km}km driven"
            )

        units_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kwh|units?)\b", lower)
        if units_match and result.energy_kwh is None:
            result.energy_kwh = float(units_match.group(1))
            result.explanations.append(f"Receipt: electricity bill, {result.energy_kwh} units (observed)")

        if result.diet_type is None:
            if any(item in lower for item in RECEIPT_MEAT_ITEMS):
                result.diet_type = "meat_heavy"
                result.inferred_fields.add("food")
                result.explanations.append("Receipt: meat items detected -- inferred meat-heavy diet")
            elif any(item in lower for item in RECEIPT_VEG_ITEMS):
                result.diet_type = "vegetarian"
                result.inferred_fields.add("food")
                result.explanations.append("Receipt: vegetarian items detected -- inferred vegetarian diet")

    # --- diet (general text) ---
    if result.diet_type is None:
        diet = _find_keyword(lower, DIET_KEYWORDS)
        if diet:
            result.diet_type = diet
            result.explanations.append(f"Food: '{diet}' mentioned (observed)")

    # --- energy (general text) ---
    if result.energy_kwh is None:
        kwh = _find_energy_kwh(lower)
        if kwh is not None:
            result.energy_kwh = kwh
            result.explanations.append(f"Energy: {kwh}kWh (observed)")
        else:
            level = _find_keyword(lower, ENERGY_LEVEL_KEYWORDS)
            if level:
                result.energy_level = level
                result.explanations.append(f"Energy: '{level}' usage mentioned (observed)")

    return result
