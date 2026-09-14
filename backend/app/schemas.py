from datetime import date as date_type
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from .emission_factors import (
    DIET_FACTORS_KG_PER_DAY,
    ENERGY_LEVEL_KWH,
    FLIGHT_FACTORS_KG_PER_KM,
    REGIONS,
    SHOPPING_LEVEL_KG_PER_DAY,
)

Channel = Literal["form", "natural_language", "voice", "receipt"]


def _valid_commute_mode(v, region_code: str = "IN"):
    # Commute modes are the same key set across all regions; validate
    # against any one region's keys.
    valid = REGIONS[region_code]["commute_kg_per_km"].keys()
    if v is not None and v not in valid:
        raise ValueError(f"commute_mode must be one of {list(valid)}")
    return v


def _valid_flight_haul(v):
    if v is not None and v not in FLIGHT_FACTORS_KG_PER_KM:
        raise ValueError(f"flight_haul must be one of {list(FLIGHT_FACTORS_KG_PER_KM)}")
    return v


def _valid_shopping_level(v):
    if v is not None and v not in SHOPPING_LEVEL_KG_PER_DAY:
        raise ValueError(f"shopping_level must be one of {list(SHOPPING_LEVEL_KG_PER_DAY)}")
    return v


class LogEntryIn(BaseModel):
    """What the client sends when logging (or updating) a day."""

    date: date_type
    commute_mode: Optional[str] = None
    commute_distance_km: Optional[float] = None
    diet_type: Optional[str] = None
    energy_kwh: Optional[float] = None
    energy_level: Optional[str] = None
    flight_km: Optional[float] = None
    flight_haul: Optional[str] = None
    shopping_level: Optional[str] = None
    notes: Optional[str] = None
    region: str = "IN"
    channel: Channel = "form"
    inferred_fields: list[str] = []

    @field_validator("commute_mode")
    @classmethod
    def valid_commute_mode(cls, v):
        return _valid_commute_mode(v)

    @field_validator("diet_type")
    @classmethod
    def valid_diet_type(cls, v):
        if v is not None and v not in DIET_FACTORS_KG_PER_DAY:
            raise ValueError(f"diet_type must be one of {list(DIET_FACTORS_KG_PER_DAY)}")
        return v

    @field_validator("energy_level")
    @classmethod
    def valid_energy_level(cls, v):
        if v is not None and v not in ENERGY_LEVEL_KWH:
            raise ValueError(f"energy_level must be one of {list(ENERGY_LEVEL_KWH)}")
        return v

    @field_validator("flight_haul")
    @classmethod
    def valid_flight_haul(cls, v):
        return _valid_flight_haul(v)

    @field_validator("shopping_level")
    @classmethod
    def valid_shopping_level(cls, v):
        return _valid_shopping_level(v)

    @field_validator("region")
    @classmethod
    def valid_region(cls, v):
        if v not in REGIONS:
            raise ValueError(f"region must be one of {list(REGIONS)}")
        return v


class CategoryEstimate(BaseModel):
    kg_co2e: float
    source: Literal["observed", "inferred", "personal_estimate", "population_default"]
    uncertainty_pct: float
    low_kg_co2e: float
    high_kg_co2e: float
    basis: Optional[Literal["weekday_average", "rolling_average"]] = None


class LogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date_type
    commute_mode: Optional[str] = None
    commute_distance_km: Optional[float] = None
    diet_type: Optional[str] = None
    energy_kwh: Optional[float] = None
    energy_level: Optional[str] = None
    flight_km: Optional[float] = None
    flight_haul: Optional[str] = None
    shopping_level: Optional[str] = None
    notes: Optional[str] = None
    region: str
    channel: str

    commute: CategoryEstimate
    food: CategoryEstimate
    energy: CategoryEstimate
    flights: CategoryEstimate
    shopping: CategoryEstimate
    total_kg_co2e: float
    total_low_kg_co2e: float
    total_high_kg_co2e: float
    factor_version: str


class SummaryOut(BaseModel):
    days_logged: int
    total_kg_co2e: float
    average_kg_co2e_per_day: float
    category_totals: dict[str, float]
    trend: list[LogEntryOut]


class RegionOut(BaseModel):
    code: str
    label: str
    version: str


class ParseRequest(BaseModel):
    text: str
    channel: Channel = "natural_language"
    region: str = "IN"

    @field_validator("region")
    @classmethod
    def valid_region(cls, v):
        if v not in REGIONS:
            raise ValueError(f"region must be one of {list(REGIONS)}")
        return v


class ParseResponse(BaseModel):
    date: date_type
    commute_mode: Optional[str] = None
    commute_distance_km: Optional[float] = None
    diet_type: Optional[str] = None
    energy_kwh: Optional[float] = None
    energy_level: Optional[str] = None
    flight_km: Optional[float] = None
    flight_haul: Optional[str] = None
    shopping_level: Optional[str] = None
    inferred_fields: list[str] = []
    notes: Optional[str] = None
    raw_text: str
    explanations: list[str] = []


class SimulateRequest(BaseModel):
    commute_mode: Optional[str] = None
    commute_distance_km: Optional[float] = None
    diet_type: Optional[str] = None
    energy_kwh: Optional[float] = None
    energy_level: Optional[str] = None
    flight_km: Optional[float] = None
    flight_haul: Optional[str] = None
    shopping_level: Optional[str] = None
    region: str = "IN"

    @field_validator("commute_mode")
    @classmethod
    def valid_commute_mode(cls, v):
        return _valid_commute_mode(v)

    @field_validator("flight_haul")
    @classmethod
    def valid_flight_haul(cls, v):
        return _valid_flight_haul(v)

    @field_validator("shopping_level")
    @classmethod
    def valid_shopping_level(cls, v):
        return _valid_shopping_level(v)

    @field_validator("region")
    @classmethod
    def valid_region(cls, v):
        if v not in REGIONS:
            raise ValueError(f"region must be one of {list(REGIONS)}")
        return v


class SimulateResponse(BaseModel):
    commute: CategoryEstimate
    food: CategoryEstimate
    energy: CategoryEstimate
    flights: CategoryEstimate
    shopping: CategoryEstimate
    total_kg_co2e: float
    baseline_kg_co2e: Optional[float] = None
    delta_kg_co2e: Optional[float] = None


class ForecastPoint(BaseModel):
    date: date_type
    projected_kg_co2e: float
    low_kg_co2e: float
    high_kg_co2e: float


class ForecastOut(BaseModel):
    method: str
    basis_days: int
    points: list[ForecastPoint]


class OptimizeRequest(BaseModel):
    target_kg_per_day: float
    region: str = "IN"

    @field_validator("region")
    @classmethod
    def valid_region(cls, v):
        if v not in REGIONS:
            raise ValueError(f"region must be one of {list(REGIONS)}")
        return v


class OptimizeAction(BaseModel):
    lever: str
    change: str
    kg_saved_per_day: float
    rationale: str


class OptimizeOut(BaseModel):
    baseline_kg_per_day: float
    target_kg_per_day: float
    projected_kg_per_day: float
    achievable: bool
    actions: list[OptimizeAction]


class Insight(BaseModel):
    type: str
    headline: str
    detail: str
    severity: Literal["info", "positive", "warning"] = "info"


class InsightsOut(BaseModel):
    generated_from_days: int
    insights: list[Insight]


# --------------------------------------------------------------- anomalies (7)

class AnomalyOut(BaseModel):
    date: date_type
    total_kg_co2e: float
    modified_z_score: float
    direction: Literal["high", "low"]
    primary_category: str
    message: str


class AnomaliesOut(BaseModel):
    baseline_days: int
    anomalies: list[AnomalyOut]


# --------------------------------------------------------------- patterns (9)

class WeekdayAverageOut(BaseModel):
    weekday: int
    label: str
    average_kg_co2e: float
    days_sampled: int


class PatternsOut(BaseModel):
    enough_data: bool
    weekdays: list[WeekdayAverageOut]
    highest: Optional[WeekdayAverageOut] = None
    lowest: Optional[WeekdayAverageOut] = None


# ----------------------------------------------------------------- budget (13)

class BudgetIn(BaseModel):
    target_kg_per_day: float


class BudgetOut(BaseModel):
    target_kg_per_day: float
    created_date: date_type


class DailyBudgetStatus(BaseModel):
    date: date_type
    total_kg_co2e: float
    under_budget: bool


class BudgetStatusOut(BaseModel):
    target_kg_per_day: float
    created_date: date_type
    days_tracked: int
    days_under_budget: int
    current_streak: int
    best_streak: int
    daily_status: list[DailyBudgetStatus]
