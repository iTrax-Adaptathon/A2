from datetime import date as date_type

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, SessionLocal, engine
from .emission_factors import (
    DIET_FACTORS_KG_PER_DAY,
    ENERGY_LEVEL_KWH,
    list_regions,
    REGIONS,
)
from .estimator import estimate_entry
from .forecast import forecast as run_forecast
from .insights import generate_insights
from .nlp_parser import parse_text
from .optimizer import optimize as run_optimize

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


def _history_for(entry: models.LogEntry, all_entries: list[models.LogEntry]) -> list[models.LogEntry]:
    # Most-recent-date-first, as estimate_entry's rolling average expects.
    return sorted((e for e in all_entries if e.id != entry.id), key=lambda e: e.date, reverse=True)


def _to_out(entry: models.LogEntry, all_entries: list[models.LogEntry]) -> schemas.LogEntryOut:
    history = _history_for(entry, all_entries)
    result = estimate_entry(entry, history, entry.region)
    return schemas.LogEntryOut(
        date=entry.date,
        commute_mode=entry.commute_mode,
        commute_distance_km=entry.commute_distance_km,
        diet_type=entry.diet_type,
        energy_kwh=entry.energy_kwh,
        energy_level=entry.energy_level,
        notes=entry.notes,
        region=entry.region,
        channel=entry.channel,
        commute=schemas.CategoryEstimate(**vars(result["commute"])),
        food=schemas.CategoryEstimate(**vars(result["food"])),
        energy=schemas.CategoryEstimate(**vars(result["energy"])),
        total_kg_co2e=result["total_kg_co2e"],
        total_low_kg_co2e=result["total_low_kg_co2e"],
        total_high_kg_co2e=result["total_high_kg_co2e"],
        factor_version=result["factor_version"],
    )


# ---------------------------------------------------------------- reference

@app.get("/api/reference")
def reference():
    """Lets the frontend build its form options from the same source of truth as the estimator."""
    any_region = next(iter(REGIONS.values()))
    return {
        "commute_modes": list(any_region["commute_kg_per_km"].keys()),
        "diet_types": list(DIET_FACTORS_KG_PER_DAY.keys()),
        "energy_levels": list(ENERGY_LEVEL_KWH.keys()),
    }


@app.get("/api/regions", response_model=list[schemas.RegionOut])
def regions():
    return list_regions()


# --------------------------------------------------------------------- logs

@app.post("/api/logs", response_model=schemas.LogEntryOut)
def upsert_log(payload: schemas.LogEntryIn):
    """Create or overwrite the log entry for a given date (one entry per day)."""
    db = _db()
    try:
        existing = db.execute(
            select(models.LogEntry).where(models.LogEntry.date == payload.date)
        ).scalar_one_or_none()

        data = payload.model_dump(exclude={"date", "inferred_fields"})

        if existing:
            for field, value in data.items():
                setattr(existing, field, value)
            existing.inferred_fields = set(payload.inferred_fields)
            entry = existing
        else:
            entry = models.LogEntry(date=payload.date, **data)
            entry.inferred_fields = set(payload.inferred_fields)
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


# ------------------------------------------------------------------ summary

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


# --------------------------------------------------------- multi-modal input

@app.post("/api/logs/parse", response_model=schemas.ParseResponse)
def parse_log_text(payload: schemas.ParseRequest):
    """
    Shared entry point for the natural-language, voice, and receipt
    channels: turns free text (typed, transcribed, or OCR'd client-side)
    into structured fields *without saving*, so the frontend can show a
    "here's what we detected" preview the user can edit before POSTing
    to /api/logs.
    """
    parsed = parse_text(payload.text, channel=payload.channel)
    return schemas.ParseResponse(
        date=parsed.date,
        commute_mode=parsed.commute_mode,
        commute_distance_km=parsed.commute_distance_km,
        diet_type=parsed.diet_type,
        energy_kwh=parsed.energy_kwh,
        energy_level=parsed.energy_level,
        inferred_fields=sorted(parsed.inferred_fields),
        notes=payload.text,
        raw_text=payload.text,
        explanations=parsed.explanations,
    )


# ------------------------------------------------------------- what-if (10)

@app.post("/api/simulate", response_model=schemas.SimulateResponse)
def simulate(payload: schemas.SimulateRequest):
    """Computes a hypothetical day's footprint without persisting it,
    and compares it against the user's current personal average."""
    db = _db()
    try:
        all_entries = db.execute(select(models.LogEntry)).scalars().all()
        history = sorted(all_entries, key=lambda e: e.date, reverse=True)

        class _Hypothetical:
            pass

        h = _Hypothetical()
        h.commute_mode = payload.commute_mode
        h.commute_distance_km = payload.commute_distance_km
        h.diet_type = payload.diet_type
        h.energy_kwh = payload.energy_kwh
        h.energy_level = payload.energy_level
        h.inferred_fields = set()

        result = estimate_entry(h, history, payload.region)

        baseline = None
        delta = None
        if all_entries:
            latest = max(all_entries, key=lambda e: e.date)
            baseline_history = sorted((e for e in all_entries if e.id != latest.id), key=lambda e: e.date, reverse=True)
            baseline_result = estimate_entry(latest, baseline_history, payload.region)
            baseline = baseline_result["total_kg_co2e"]
            delta = round(result["total_kg_co2e"] - baseline, 2)

        return schemas.SimulateResponse(
            commute=schemas.CategoryEstimate(**vars(result["commute"])),
            food=schemas.CategoryEstimate(**vars(result["food"])),
            energy=schemas.CategoryEstimate(**vars(result["energy"])),
            total_kg_co2e=result["total_kg_co2e"],
            baseline_kg_co2e=baseline,
            delta_kg_co2e=delta,
        )
    finally:
        db.close()


# -------------------------------------------------------------- forecast (8)

@app.get("/api/forecast", response_model=schemas.ForecastOut)
def forecast_endpoint(days: int = 7):
    db = _db()
    try:
        all_entries = db.execute(select(models.LogEntry)).scalars().all()
        ordered = sorted(all_entries, key=lambda e: e.date)
        trend = [_to_out(e, all_entries) for e in ordered]
        result = run_forecast(trend, days=days)
        return schemas.ForecastOut(
            method=result["method"],
            basis_days=result["basis_days"],
            points=[schemas.ForecastPoint(**vars(p)) for p in result["points"]],
        )
    finally:
        db.close()


# -------------------------------------------------------------- optimize (11)

@app.post("/api/optimize", response_model=schemas.OptimizeOut)
def optimize_endpoint(payload: schemas.OptimizeRequest):
    db = _db()
    try:
        all_entries = db.execute(select(models.LogEntry)).scalars().all()
        result = run_optimize(all_entries, payload.target_kg_per_day, payload.region)
        return schemas.OptimizeOut(
            baseline_kg_per_day=result["baseline_kg_per_day"],
            target_kg_per_day=result["target_kg_per_day"],
            projected_kg_per_day=result["projected_kg_per_day"],
            achievable=result["achievable"],
            actions=[schemas.OptimizeAction(**vars(a)) for a in result["actions"]],
        )
    finally:
        db.close()


# --------------------------------------------------------------- insights (15)

@app.get("/api/insights", response_model=schemas.InsightsOut)
def insights_endpoint(region: str = "IN"):
    db = _db()
    try:
        all_entries = db.execute(select(models.LogEntry)).scalars().all()
        ordered = sorted(all_entries, key=lambda e: e.date)
        trend = [_to_out(e, all_entries) for e in ordered]
        raw = generate_insights(trend, all_entries, region)
        return schemas.InsightsOut(
            generated_from_days=len(trend),
            insights=[schemas.Insight(**i) for i in raw],
        )
    finally:
        db.close()
