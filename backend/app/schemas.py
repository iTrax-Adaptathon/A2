from datetime import date as date_type
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from .emission_factors import (
    COMMUTE_FACTORS_KG_PER_KM,
    DIET_FACTORS_KG_PER_DAY,
    ENERGY_LEVEL_KWH,
)


class LogEntryIn(BaseModel):
    """What the client sends when logging (or updating) a day."""

    date: date_type
    commute_mode: Optional[str] = None
    commute_distance_km: Optional[float] = None
    diet_type: Optional[str] = None
    energy_kwh: Optional[float] = None
    energy_level: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("commute_mode")
    @classmethod
    def valid_commute_mode(cls, v):
        if v is not None and v not in COMMUTE_FACTORS_KG_PER_KM:
            raise ValueError(f"commute_mode must be one of {list(COMMUTE_FACTORS_KG_PER_KM)}")
        return v

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


class CategoryEstimate(BaseModel):
    """One category's contribution to a day's footprint, plus how it was derived."""

    kg_co2e: float
    source: Literal["logged", "estimated", "default"]


class LogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date_type
    commute_mode: Optional[str] = None
    commute_distance_km: Optional[float] = None
    diet_type: Optional[str] = None
    energy_kwh: Optional[float] = None
    energy_level: Optional[str] = None
    notes: Optional[str] = None

    commute: CategoryEstimate
    food: CategoryEstimate
    energy: CategoryEstimate
    total_kg_co2e: float


class SummaryOut(BaseModel):
    days_logged: int
    total_kg_co2e: float
    average_kg_co2e_per_day: float
    category_totals: dict[str, float]
    trend: list[LogEntryOut]
