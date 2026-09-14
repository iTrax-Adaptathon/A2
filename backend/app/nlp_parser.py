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

from .emission_factors import FLIGHT_HAUL_DEFAULT_KM, LONG_HAUL_THRESHOLD_KM

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

FLIGHT_KEYWORDS = ["flew", "flight", "flying", "plane", "airplane", "air travel"]
LONG_HAUL_KEYWORDS = ["international", "long haul", "long-haul", "abroad", "overseas"]
SHORT_HAUL_KEYWORDS = ["domestic", "short haul", "short-haul", "local flight"]

SHOPPING_KEYWORDS = ["bought", "shopping", "shopped", "purchased", "ordered", "new clothes", "online order"]
HIGH_SHOPPING_KEYWORDS = ["big shopping", "lots of shopping", "a lot of shopping", "shopping spree", "bought a lot"]
LOW_SHOPPING_KEYWORDS = ["small order", "just a few things", "bought a little", "one item"]

RECEIPT_SHOPPING_STORE_KEYWORDS = [
    "mall", "amazon", "flipkart", "myntra", "clothing", "shoes", "electronics", "gadget", "order confirmed",
]


@dataclass
class ParsedResult:
    date: date_type
    commute_mode: str | None = None
    commute_distance_km: float | None = None
    diet_type: str | None = None
    energy_kwh: float | None = None
    energy_level: str | None = None
    flight_km: float | None = None
    flight_haul: str | None = None
    shopping_level: str | None = None
    inferred_fields: set = field(default_factory=set)
    explanations: list = field(default_factory=list)


def _find_keyword(text: str, keyword_map: dict) -> str | None:
    for key, words in keyword_map.items():
        for w in words:
            if w and w in text:
                return key
    return None


def _find_all_distances_km(text: str) -> list[float]:
    """All distance mentions in the order they appear, km and miles
    normalized to km -- used positionally so multiple distances in one
    sentence (e.g. a commute AND a flight) get assigned to the right
    field rather than both grabbing the first number."""
    out = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(km|kilometers?|kilometres?|mi|miles?)\b", text):
        value = float(m.group(1))
        km = value * MILES_TO_KM if m.group(2).startswith("mi") else value
        out.append(round(km, 1))
    return out


def _find_energy_kwh(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kwh|units?)\b", text)
    return float(match.group(1)) if match else None


def _find_amount(text: str) -> float | None:
    match = re.search(r"total\D{0,10}?(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def parse_text(text: str, channel: str = "natural_language", today: date_type | None = None) -> ParsedResult:
    today = today or date_type.today()
    lower = text.lower()

    result = ParsedResult(date=today)

    if "yesterday" in lower:
        result.date = today - timedelta(days=1)

    # Distances are consumed positionally (first mention -> commute,
    # next -> flight) so "drove 10km then flew 2000km" assigns each
    # number to the right field instead of both grabbing the first one.
    distances = _find_all_distances_km(lower)
    distance_cursor = 0

    # --- commute ---
    mode = _find_keyword(lower, COMMUTE_KEYWORDS)
    if mode:
        result.commute_mode = mode
        if mode == "wfh":
            result.commute_distance_km = 0.0
            result.explanations.append("Commute: work from home (0km)")
        elif distance_cursor < len(distances):
            result.commute_distance_km = distances[distance_cursor]
            distance_cursor += 1
            result.explanations.append(f"Commute: {mode}, {result.commute_distance_km}km (stated)")
        else:
            # Mode named but no distance -- fill a typical assumption and
            # flag it as inferred rather than observed.
            result.commute_distance_km = 10.0
            result.inferred_fields.add("commute")
            result.explanations.append(
                f"Commute: detected '{mode}' but no distance -- assumed a typical 10km"
            )

    # --- flights ---
    if any(kw in lower for kw in FLIGHT_KEYWORDS):
        distance_stated = distance_cursor < len(distances)
        if distance_stated:
            result.flight_km = distances[distance_cursor]
            distance_cursor += 1

        if any(kw in lower for kw in LONG_HAUL_KEYWORDS):
            result.flight_haul = "long"
        elif any(kw in lower for kw in SHORT_HAUL_KEYWORDS):
            result.flight_haul = "short"
        elif result.flight_km is not None:
            result.flight_haul = "long" if result.flight_km >= LONG_HAUL_THRESHOLD_KM else "short"
        else:
            result.flight_haul = "short"

        if not distance_stated:
            result.flight_km = FLIGHT_HAUL_DEFAULT_KM[result.flight_haul]
            result.inferred_fields.add("flights")
            result.explanations.append(
                f"Flight: detected but no distance stated -- assumed {result.flight_haul}-haul ~{result.flight_km}km"
            )
        else:
            result.explanations.append(f"Flight: {result.flight_haul}-haul, {result.flight_km}km (stated)")

    # --- shopping ---
    if any(kw in lower for kw in SHOPPING_KEYWORDS):
        if any(kw in lower for kw in HIGH_SHOPPING_KEYWORDS):
            result.shopping_level = "high"
            result.explanations.append("Shopping: 'high' intensity mentioned (observed)")
        elif any(kw in lower for kw in LOW_SHOPPING_KEYWORDS):
            result.shopping_level = "low"
            result.explanations.append("Shopping: 'low' intensity mentioned (observed)")
        else:
            result.shopping_level = "medium"
            result.inferred_fields.add("shopping")
            result.explanations.append("Shopping: mentioned but no intensity stated -- assumed medium")

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

        if result.shopping_level is None and any(kw in lower for kw in RECEIPT_SHOPPING_STORE_KEYWORDS):
            amount = _find_amount(lower)
            if amount is not None and amount > 2000:
                result.shopping_level = "high"
            elif amount is not None and amount < 500:
                result.shopping_level = "low"
            else:
                result.shopping_level = "medium"
            result.inferred_fields.add("shopping")
            amount_note = f"total {amount:.0f}" if amount is not None else "no total found"
            result.explanations.append(
                f"Receipt: shopping store detected ({amount_note}) -- inferred {result.shopping_level} shopping"
            )

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
