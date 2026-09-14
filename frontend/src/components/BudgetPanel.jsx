import { useEffect, useState } from "react";
import { clearBudget, getBudget, getBudgetStatus, setBudget } from "../api";

export default function BudgetPanel({ summary }) {
  const [budget, setBudgetState] = useState(undefined); // undefined = loading, null = none set
  const [status, setStatus] = useState(null);
  const [target, setTarget] = useState(
    summary?.average_kg_co2e_per_day ? Math.round(summary.average_kg_co2e_per_day * 0.8) : 10
  );
  const [saving, setSaving] = useState(false);

  function refresh() {
    getBudget().then(setBudgetState);
  }

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (budget) {
      getBudgetStatus().then(setStatus);
    } else {
      setStatus(null);
    }
  }, [budget]);

  async function handleSet(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const b = await setBudget(Number(target));
      setBudgetState(b);
    } finally {
      setSaving(false);
    }
  }

  async function handleClear() {
    await clearBudget();
    setBudgetState(null);
    setStatus(null);
  }

  if (budget === undefined) return null;

  return (
    <div className="card">
      <div className="section-header">
        <h2>Carbon budget</h2>
        <span className="pill">persisted &middot; streaks</span>
      </div>
      <p className="hint">
        Unlike the Optimizer's ad-hoc target, this budget is saved and tracked over time &mdash;
        every day since you set it counts toward a streak.
      </p>

      {!budget ? (
        <form className="budget-setup" onSubmit={handleSet}>
          <label>
            Daily target: {target} kg CO2e/day
            <input type="range" min="1" max="30" step="0.5" value={target} onChange={(e) => setTarget(e.target.value)} />
          </label>
          <button type="submit" disabled={saving}>
            {saving ? "Setting..." : "Set budget"}
          </button>
        </form>
      ) : (
        <>
          <div className="budget-summary">
            <div>
              <span className="stat-value">{budget.target_kg_per_day}</span>
              <span className="stat-label">kg/day target</span>
            </div>
            <div>
              <span className="stat-value stat-positive">{status?.current_streak ?? 0}</span>
              <span className="stat-label">current streak</span>
            </div>
            <div>
              <span className="stat-value">{status?.best_streak ?? 0}</span>
              <span className="stat-label">best streak</span>
            </div>
            <div>
              <span className="stat-value">
                {status?.days_tracked ? `${status.days_under_budget}/${status.days_tracked}` : "0/0"}
              </span>
              <span className="stat-label">days under budget</span>
            </div>
          </div>

          {status?.daily_status?.length > 0 && (
            <div className="budget-strip">
              {status.daily_status.map((d) => (
                <span
                  key={d.date}
                  className={`budget-dot ${d.under_budget ? "under" : "over"}`}
                  title={`${d.date}: ${d.total_kg_co2e}kg (${d.under_budget ? "under" : "over"} budget)`}
                />
              ))}
            </div>
          )}

          <p className="hint">Since {budget.created_date}. Set a new target to reset tracking.</p>

          <form className="budget-setup" onSubmit={handleSet}>
            <label>
              New target: {target} kg CO2e/day
              <input type="range" min="1" max="30" step="0.5" value={target} onChange={(e) => setTarget(e.target.value)} />
            </label>
            <div className="budget-actions">
              <button type="submit" disabled={saving}>
                {saving ? "Updating..." : "Update budget"}
              </button>
              <button type="button" className="secondary" onClick={handleClear}>
                Clear
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  );
}
