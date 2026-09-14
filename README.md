# Personal Carbon Footprint Tracker

Built for **Adaptathon (Techkshetra'26) — Q2, Sprint 1**.

> Each problem statement defines only what the first team builds in Sprint 1.
> What the next team does with it after handoff is entirely open-ended — so
> this README exists mainly for *them*.

## What it does

Users log daily lifestyle choices (commute, food, energy use) and get an
estimated carbon footprint (kg CO2e), visualized as a trend over time.
Logging is expected to be **irregular and incomplete** — the interesting
part of this problem isn't the CRUD, it's staying meaningful when a user
skips fields or whole days.

## How incomplete logging is handled (the core challenge)

For each of the three categories (commute, food, energy) on a given day,
`backend/app/estimator.py` resolves a value in this priority order:

1. **`logged`** — the user gave enough info to compute it directly.
2. **`estimated`** — missing, but the user has enough of their *own* history
   in that category (last 14 data points) to fall back to their personal
   average instead of guessing blind or zeroing it out.
3. **`default`** — no personal history yet either (e.g. very first log), so
   it falls back to a population-average constant just so day one isn't
   misleadingly reported as zero.

Every category result carries its `source` alongside the number. The
frontend never hides this — the chart tooltip shows `(logged)` /
`(estimated)` / `(default)` per category so a user (or a judge) can see how
much of a given day's total is real vs. inferred.

**Design note:** estimates are recomputed from the *current* full history on
every read, not frozen at write time. This means an early "estimated" day
can shift slightly as more real data comes in later — a deliberate choice
(it always reflects your latest personal average) but worth knowing if you
extend this.

## Architecture

```
backend/                  FastAPI + SQLite
  app/
    emission_factors.py   All tunable constants — swap the model here
    estimator.py          Pure logic, no DB/HTTP imports — unit-testable in isolation
    models.py              SQLAlchemy table (one row per day, all fields nullable)
    schemas.py             Pydantic request/response shapes
    main.py                Routes (upsert/list/get/delete log, summary)
  requirements.txt

frontend/                 React + Vite
  src/
    api.js                 Thin axios wrapper over the backend
    components/
      LogForm.jsx           Daily entry form
      SummaryCards.jsx       Totals + biggest-contributor category
      TrendsChart.jsx         Stacked bar chart w/ source-aware tooltip (recharts)
    App.jsx
```

No auth, single implicit user, SQLite file on disk. Deliberately minimal —
optimized for the next team to read in one pass, not for production scale.

## Running it

**Backend** (Python 3.12+):
```bash
cd backend
python -m venv venv
./venv/Scripts/activate        # Windows; source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node 18+):
```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

The frontend expects the API at `http://127.0.0.1:8000` by default; override
with a `VITE_API_URL` env var if needed.

**Backend tests** (unit tests for the estimator, no DB/HTTP needed):
```bash
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v
```

## API

| Method | Path              | Purpose                                   |
|--------|-------------------|--------------------------------------------|
| GET    | `/api/reference`  | Valid commute modes / diet types / energy levels (form options, kept in sync with the estimator) |
| POST   | `/api/logs`       | Create or overwrite the entry for a date  |
| GET    | `/api/logs`       | All entries, estimated, sorted by date    |
| GET    | `/api/logs/{date}`| One entry                                  |
| DELETE | `/api/logs/{date}`| Remove an entry                            |
| GET    | `/api/summary`    | Totals, per-day average, category breakdown, full trend |

## Emission factors

`backend/app/emission_factors.py` — rough India-weighted averages, good
enough for **relative** comparison ("commuting by car costs you more than
the bus") but not for scientific/regulatory carbon accounting. Swap them
out per-region, or replace the whole lookup with a real emissions API,
without touching anything else — that's the point of keeping them isolated.

## Where a Sprint 2 team would likely start

- **Auth / multi-user.** Everything currently assumes one implicit user.
- **Smarter imputation.** The rolling-average fallback in `estimator.py` is
  intentionally simple (mean of last 14 points) — a good seam for a
  trend-aware or weighted model.
- **Richer inputs.** Diet/energy are currently coarse categories; real
  per-meal or per-appliance logging would sit in `models.py` / `schemas.py`.
- **Goals & nudges.** The problem statement mentions informing behavior —
  there's no goal-setting or comparison-to-average-user feature yet.

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
