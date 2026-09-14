import { useState } from "react";
import { optimize } from "../api";

export default function OptimizerPanel({ region, summary }) {
  const defaultTarget = summary?.average_kg_co2e_per_day
    ? Math.max(Math.round(summary.average_kg_co2e_per_day * 0.7 * 10) / 10, 1)
    : 8;
  const [target, setTarget] = useState(defaultTarget);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleOptimize() {
    setLoading(true);
    try {
      const r = await optimize(Number(target), region);
      setResult(r);
    } finally {
      setLoading(false);
    }
  }

  const maxSaving = result?.actions.length ? Math.max(...result.actions.map((a) => a.kg_saved_per_day)) : 1;

  return (
    <div className="card">
      <div className="section-header">
        <h2>Carbon budget optimizer</h2>
        <span className="pill">constraint-based</span>
      </div>
      <p className="hint">
        Set a target kg CO2e/day and get the smallest set of lifestyle changes — ranked by
        impact — that gets you there, based on your logged history.
      </p>

      <div className="optimizer-input">
        <label>
          Target: {target} kg CO2e/day
          <input
            type="range"
            min="1"
            max="30"
            step="0.5"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
          />
        </label>
        <button type="button" onClick={handleOptimize} disabled={loading}>
          {loading ? "Optimizing..." : "Optimize"}
        </button>
      </div>

      {result && (
        <div className="optimizer-result">
          <div className="optimizer-summary">
            <div>
              <span className="stat-value">{result.baseline_kg_per_day}</span>
              <span className="stat-label">current baseline</span>
            </div>
            <span className="arrow">&rarr;</span>
            <div>
              <span className={`stat-value ${result.achievable ? "stat-positive" : "stat-warning"}`}>
                {result.projected_kg_per_day}
              </span>
              <span className="stat-label">
                projected {result.achievable ? "(target met)" : "(target not fully reached)"}
              </span>
            </div>
          </div>

          {result.actions.length === 0 ? (
            <p className="hint">You're already at or below this target &mdash; no changes needed.</p>
          ) : (
            <ol className="action-list">
              {result.actions.map((a, i) => (
                <li key={i}>
                  <div className="action-row">
                    <span className="action-lever">{a.lever}</span>
                    <span className="action-change">{a.change}</span>
                    <span className="action-saving">-{a.kg_saved_per_day}kg/day</span>
                  </div>
                  <div className="action-bar-track">
                    <div
                      className={`action-bar-fill lever-${a.lever}`}
                      style={{ width: `${(a.kg_saved_per_day / maxSaving) * 100}%` }}
                    />
                  </div>
                  <p className="action-rationale">{a.rationale}</p>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
