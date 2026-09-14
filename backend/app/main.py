from datetime import date as date_type

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, SessionLocal, engine
from .emission_factors import (
    COMMUTE_FACTORS_KG_PER_KM,
    DIET_FACTORS_KG_PER_DAY,
    ENERGY_LEVEL_KWH,
)
from .estimator import estimate_entry

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Carbon Footprint Tracker")

# Wide-open CORS: this is a Sprint 1 hackathon build with no auth yet.
# Tighten this before it ever sees a real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _db() -> Session:
    return SessionLocal()


def _to_out(entry: models.LogEntry, all_entries: list[models.LogEntry]) -> schemas.LogEntryOut:
    history = [e for e in all_entries if e.id != entry.id]
    result = estimate_entry(entry, history)
    return schemas.LogEntryOut(
        date=entry.date,
        commute_mode=entry.commute_mode,
        commute_distance_km=entry.commute_distance_km,
        diet_type=entry.diet_type,
        energy_kwh=entry.energy_kwh,
        energy_level=entry.energy_level,
        notes=entry.notes,
        commute=schemas.CategoryEstimate(**vars(result["commute"])),
        food=schemas.CategoryEstimate(**vars(result["food"])),
        energy=schemas.CategoryEstimate(**vars(result["energy"])),
        total_kg_co2e=result["total_kg_co2e"],
    )


@app.get("/api/reference")
def reference():
    """Lets the frontend build its form options from the same source of truth as the estimator."""
    return {
        "commute_modes": list(COMMUTE_FACTORS_KG_PER_KM.keys()),
        "diet_types": list(DIET_FACTORS_KG_PER_DAY.keys()),
        "energy_levels": list(ENERGY_LEVEL_KWH.keys()),
    }


@app.post("/api/logs", response_model=schemas.LogEntryOut)
def upsert_log(payload: schemas.LogEntryIn):
    """Create or overwrite the log entry for a given date (one entry per day)."""
    db = _db()
    try:
        existing = db.execute(
            select(models.LogEntry).where(models.LogEntry.date == payload.date)
        ).scalar_one_or_none()

        if existing:
            for field, value in payload.model_dump(exclude={"date"}).items():
                setattr(existing, field, value)
            entry = existing
        else:
            entry = models.LogEntry(**payload.model_dump())
            db.add(entry)

        db.commit()
        db.refresh(entry)

        all_entries = db.execute(select(models.LogEntry)).scalars().all()
        return _to_out(entry, all_entries)
    finally:
        db.close()


@app.get("/api/logs", response_model=list[schemas.LogEntryOut])
def list_logs():
    db = _db()
    try:
        all_entries = db.execute(select(models.LogEntry)).scalars().all()
        ordered = sorted(all_entries, key=lambda e: e.date)
        return [_to_out(e, all_entries) for e in ordered]
    finally:
        db.close()


@app.get("/api/logs/{log_date}", response_model=schemas.LogEntryOut)
def get_log(log_date: date_type):
    db = _db()
    try:
        all_entries = db.execute(select(models.LogEntry)).scalars().all()
        entry = next((e for e in all_entries if e.date == log_date), None)
        if entry is None:
            raise HTTPException(status_code=404, detail="No log for that date")
        return _to_out(entry, all_entries)
    finally:
        db.close()


@app.delete("/api/logs/{log_date}")
def delete_log(log_date: date_type):
    db = _db()
    try:
        entry = db.execute(
            select(models.LogEntry).where(models.LogEntry.date == log_date)
        ).scalar_one_or_none()
        if entry is None:
            raise HTTPException(status_code=404, detail="No log for that date")
        db.delete(entry)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.get("/api/summary", response_model=schemas.SummaryOut)
def summary():
    db = _db()
    try:
        all_entries = db.execute(select(models.LogEntry)).scalars().all()
        ordered = sorted(all_entries, key=lambda e: e.date)
        trend = [_to_out(e, all_entries) for e in ordered]

        days_logged = len(trend)
        total = round(sum(t.total_kg_co2e for t in trend), 2)
        avg = round(total / days_logged, 2) if days_logged else 0.0
        category_totals = {
            "commute": round(sum(t.commute.kg_co2e for t in trend), 2),
            "food": round(sum(t.food.kg_co2e for t in trend), 2),
            "energy": round(sum(t.energy.kg_co2e for t in trend), 2),
        }

        return schemas.SummaryOut(
            days_logged=days_logged,
            total_kg_co2e=total,
            average_kg_co2e_per_day=avg,
            category_totals=category_totals,
            trend=trend,
        )
    finally:
        db.close()
