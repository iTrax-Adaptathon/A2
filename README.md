# Carbon Emission

Personal carbon footprint tracker built for **Adaptathon (Techkshetra'26) —
Q2, Sprint 1**.

> Each problem statement defines only what the first team builds in Sprint 1.
> What the next team does with it after handoff is entirely open-ended — so
> this README exists mainly for *them*.

## What it does

Users log daily lifestyle choices across **five categories** — commute,
food, home energy, flights, and shopping/consumption — via a form, typed
natural language, voice, or a photographed receipt — and get an estimated
carbon footprint (kg CO2e), visualized as a trend with a forecast, narrated
by a rule-based analyst, and actionable through a what-if simulator and a
constraint-based optimizer. The UI is a dark "instrument panel" theme
(ember/lime accents, monospace numerics, a distinct color per category used
consistently in every chart, badge, and bar) rather than a generic light
SaaS dashboard.

**Beyond commute/food/energy**, the two added categories reflect real
contributors to a personal footprint that a 3-category model misses:

- **Flights** — often the single largest line item in a real footprint (a
  6000km long-haul flight ≈ 660kg CO2e, more than three weeks of daily
  commuting). Modeled as *event-based*: a day with no flight logged defaults
  to 0kg, never smeared as a personal-average guess (see below) — and
  flights are deliberately **not** offered as an Optimizer lever, since a
  trip that already happened has no smaller substitute.
- **Shopping/consumption** — modeled as an amortized daily level (low/medium/
  high), the same style as energy usage, since most people don't log every
  purchase.

Of the fifteen possible module ideas for this problem, this build **fully
implements twelve** end-to-end (not mocked) and **previews the remaining
three** as honest "Coming in Sprint 2" cards in the Roadmap tab — described,
not faked with placeholder data.

| # | Module | Status |
|---|---|---|
| 1 | Multi-modal logging (form, NL, voice, receipt) | **Built** |
| 2 | Versioned regional emission-factor engine | **Built** |
| 3 | Carbon Digital Twin | Preview |
| 4 | Uncertainty-aware CO2 estimates | **Built** |
| 5 | Observed / inferred / estimated distinction | **Built** |
| 6 | Smart missing-data reconstruction (weekday-aware) | **Built** |
| 7 | Carbon anomaly detection | **Built** |
| 8 | Personal carbon forecasting | **Built** |
| 9 | Behavioral pattern analysis | **Built** |
| 10 | What-if simulation engine | **Built** |
| 11 | Constraint-based carbon optimization | **Built** |
| 12 | Carbon ROI ranking | Preview |
| 13 | Personalized carbon budget | **Built** |
| 14 | Carbon experiments | Preview |
| 15 | AI Carbon Analyst | **Built** |

## The core model

### Observed / inferred / personal_estimate / population_default (items 4, 5)

For each of the five categories (commute, food, energy, flights, shopping)
on a given day, `backend/app/estimator.py` resolves a value in this
priority order:

1. **`observed`** — an exact number from any channel (typed km, typed kWh, a
   meter reading pulled off a receipt).
2. **`inferred`** — a channel had to fill a gap itself, e.g. natural-language
   logging named a mode ("drove to work") without a distance, or an OCR'd
   fuel receipt was converted from litres to km.
3. **`personal_estimate`** — nothing logged this day, but the user has
   enough of their *own* recent history in this category to fall back to
   their personal average instead of guessing blind. This tier is itself
   **weekday-aware** (item 6): it first checks whether at least 2 same-
   weekday data points exist within the last 60 entries (a missing Tuesday
   looks at other Tuesdays first) and only falls back to a flat rolling
   average of the last 14 points when there isn't enough weekday-specific
   history yet. The `basis` field on each estimate (`weekday_average` vs
   `rolling_average`) records which was used — visible as a badge qualifier
   in the history table.
4. **`population_default`** — no data and no personal history yet either
   (day one), so a population-average constant is used.

**Flights are the one exception to tier 3.** They're event-based, not a
daily habit — averaging only over the days a flight *did* happen (tier 3's
normal behavior) would wrongly assume every day includes one. So a day with
no flight logged and no history skips straight to tier 4, whose default for
flights is 0kg. Shopping still uses the normal tier-3 personal average, same
as commute/food/energy.

Every result carries this source **and an uncertainty band** (item 4):
`observed` ±5%, `inferred` ±20%, `personal_estimate` ±30%,
`population_default` ±50%. A day's total combines all five categories'
uncertainty via root-sum-of-squares, so the range tightens as more of the
day is directly observed rather than guessed.

**Design note:** estimates are recomputed from the *current* full history on
every read, not frozen at write time — an early "estimated" day can shift
slightly as more real data comes in later. Deliberate, not a bug.

### Multi-modal logging (item 1)

Four input channels all converge on the same `POST /api/logs` shape:

- **Form** — exact fields, `channel: "form"`.
- **Natural language** — free text ("Drove 12km to work, had a vegetarian
  lunch") parsed by `backend/app/nlp_parser.py`, a regex/keyword engine (no
  LLM key required). Shows a "detected" preview with per-field
  observed/inferred badges before saving.
- **Voice** — the browser's Web Speech API transcribes speech to text
  client-side (Chrome/Edge; other browsers get a graceful fallback message),
  then reuses the natural-language parser.
- **Receipt** — an uploaded photo is OCR'd client-side with `tesseract.js`
  (no server-side OCR dependency), and the extracted text is parsed with
  receipt-specific rules: fuel litres → implied driving distance, an
  electricity bill's units → observed kWh, grocery item keywords → inferred
  diet type.

### Versioned regional emission-factor engine (item 2)

`backend/app/emission_factors.py` is a registry of regions (India, US, EU,
Global average), each with its own commute/energy factors **and a version
string**. Every computed estimate records which region + version produced
it. Switching the region selector in the UI only affects *new* entries and
the live tools (What-If, Optimize) — **existing logged days keep the
factors that were active when they were logged**, so historical numbers are
never silently restated if a region's factors are revised later. The
Dashboard shows an explanatory banner when this causes a visible mismatch,
rather than leaving it looking broken.

### Forecasting, simulation, optimization, analysis (items 8, 10, 11, 15)

- **Forecast** (`backend/app/forecast.py`) — least-squares regression over
  the trend (falls back to a flat average under 3 points), with an
  uncertainty band that widens the further out it projects.
- **What-if simulator** (`POST /api/simulate`) — computes a hypothetical
  day's footprint against the current region/history *without persisting
  it*, compared live against your most recent logged day.
- **Optimizer** (`backend/app/optimizer.py`) — given a target kg/day, greedily
  ranks commute/diet/energy/shopping lever changes by kg-saved-per-day and
  picks the smallest set that reaches the target. Flights are counted in the
  baseline (amortized across the whole log window) but never offered as a
  lever — see above. Deliberately a plain greedy selection over a small
  fixed catalog, not a general solver — documented as an extension seam for
  real multi-constraint optimization.
- **AI Carbon Analyst** (`backend/app/insights.py`) — a rule-based engine
  that reads the trend, forecast, optimizer, anomaly, and pattern output and
  narrates it all in plain language (trend direction, biggest contributor,
  data-quality, a flagged anomaly, a weekday pattern, a quick-win
  recommendation). No external LLM call, so it needs no API key; swapping it
  for a real LLM-backed analyst is a contained, one-file change.

### Anomaly detection, behavioral patterns, personalized budget (items 7, 9, 13)

- **Anomaly detection** (`backend/app/anomaly.py`) — flags days whose total
  deviates sharply from the user's normal pattern, using a *modified
  z-score* (median + median-absolute-deviation) rather than mean/stdev.
  This matters specifically because of flights: a single 700kg flight day
  would inflate a mean/stdev-based threshold enough to make that same day
  no longer look abnormal by the metric meant to catch it. Median/MAD is
  robust to that — a few outliers barely move the median. Surfaced via
  `GET /api/anomalies`, a Dashboard card, and the AI Analyst.
- **Behavioral pattern analysis** (`backend/app/patterns.py`) — breaks the
  trend down by weekday to show which days run highest/lowest. This is the
  same weekday-grouping the estimator uses internally for reconstruction
  (item 6) — the Dashboard's "Weekly pattern" card is effectively "show your
  work" for a strategy already running under the hood.
- **Personalized carbon budget** (`backend/app/budget.py`, its own Budget
  tab) — unlike the Optimizer's ad-hoc, one-off target, this is a
  **persisted** singleton target (`models.Budget`) tracked over time: days
  under/over budget, current streak, best streak, rendered as a
  contribution-graph-style day strip. Setting a new budget starts fresh
  from that day forward rather than retroactively judging earlier days
  against a target that didn't exist yet.

## Architecture

```
backend/                  FastAPI + SQLite
  app/
    emission_factors.py   Versioned regional factor registry
    estimator.py           Core per-day estimation (observed/inferred/estimate/default + uncertainty + weekday reconstruction)
    nlp_parser.py           Text -> structured fields (NL, voice transcript, OCR text)
    forecast.py              Linear-regression forecasting
    optimizer.py              Constraint-based greedy action ranking
    anomaly.py                 Median/MAD anomaly detection
    patterns.py                 Weekday behavioral breakdown
    budget.py                    Persisted budget streak/status math
    insights.py                   Rule-based "AI Analyst" narration
    models.py, schemas.py          DB models / request-response shapes
    main.py                         Routes
  tests/                    63 pytest cases across every module above
  requirements.txt / requirements-dev.txt

frontend/                 React + Vite
  src/
    RegionContext.jsx      Global region selection (persisted to localStorage)
    api.js                  Backend client
    components/
      Sidebar.jsx / TopBar.jsx   App shell + region selector
      LogPanel.jsx                 Tabs: Form / Natural language / Voice / Receipt
      LogForm.jsx, TextChannelLogger.jsx  The four logging channels
      SummaryCards.jsx, TrendsChart.jsx, HistoryTable.jsx  Dashboard
      PatternsCard.jsx, AnomaliesCard.jsx  Dashboard: weekday breakdown, flagged days
      InsightsFeed.jsx               AI Analyst feed
      WhatIfSimulator.jsx             Live hypothetical-day simulator
      OptimizerPanel.jsx               Ad-hoc budget-target optimizer UI
      BudgetPanel.jsx                    Persisted budget + streak tracker
      RoadmapPreview.jsx                  Honest previews of the 3 unbuilt modules
      SourceBadge.jsx                      Shared source-taxonomy badge (+ weekday/flat basis)
```

No auth, single implicit user, SQLite file on disk. Optimized for the next
team to read in one pass, not for production scale.

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
with a `VITE_API_URL` env var if needed. Voice logging needs Chrome/Edge;
receipt OCR needs internet on first use (tesseract.js fetches its language
model from a CDN).

**Backend tests:**
```bash
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/reference` | Valid commute modes / diet types / energy levels |
| GET | `/api/regions` | Region profiles + factor versions |
| POST | `/api/logs` | Create or overwrite a day's entry |
| GET | `/api/logs` | All entries, estimated, sorted by date |
| GET | `/api/logs/{date}` | One entry |
| DELETE | `/api/logs/{date}` | Remove an entry |
| GET | `/api/summary` | Totals, average, category breakdown, full trend |
| POST | `/api/logs/parse` | Parse free text (NL/voice/receipt) into structured fields, without saving |
| POST | `/api/simulate` | Hypothetical day's footprint, not persisted (What-If) |
| GET | `/api/forecast?days=7` | Projected footprint for the next N days |
| POST | `/api/optimize` | Ranked lifestyle changes to hit a target kg/day |
| GET | `/api/insights` | AI Analyst's narrated insights |
| GET | `/api/anomalies` | Days flagged by median/MAD deviation |
| GET | `/api/patterns` | Weekday averages, highest/lowest |
| POST/GET/DELETE | `/api/budget` | Set / view / clear the persisted budget |
| GET | `/api/budget/status` | Streak + under/over-budget status per day |

## Emission factors

`backend/app/emission_factors.py` — rough regional averages, good enough for
**relative** comparison ("commuting by car costs more than the bus") but not
scientific/regulatory carbon accounting.

## Where a Sprint 2 team would likely start

- **Auth / multi-user.** Everything currently assumes one implicit user
  (including the Budget singleton — it'd need a user_id column first).
- **The 3 remaining Roadmap modules** (Digital Twin, cost-weighted ROI
  ranking, structured experiments) — see the Roadmap tab for what each
  would need and why it wasn't in scope.
- **Swap the rule-based NL parser / AI Analyst for a real LLM call** — both
  are isolated modules (`nlp_parser.py`, `insights.py`) designed for exactly
  this swap.
- **Budget history.** `models.Budget` is a singleton by design (see its
  docstring) — a team wanting to compare past budget periods would need to
  stop deleting the old row on update and add a `created_date` range query
  instead.

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
