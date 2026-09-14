import { useEffect, useState } from "react";
import { getPatterns } from "../api";

export default function PatternsCard({ refreshKey }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    getPatterns().then(setData);
  }, [refreshKey]);

  if (!data) return null;

  if (!data.enough_data) {
    return (
      <div className="card">
        <h2>Weekly pattern</h2>
        <p className="hint">Log a few more days to see which weekdays run highest.</p>
      </div>
    );
  }

  const max = Math.max(...data.weekdays.map((w) => w.average_kg_co2e), 0.01);

  return (
    <div className="card">
      <div className="section-header">
        <h2>Weekly pattern</h2>
        <span className="pill">behavioral analysis</span>
      </div>
      <p className="hint">
        Average footprint by day of week, across your whole logged history &mdash; the same
        weekday grouping the estimator uses internally to fill gaps.
      </p>
      <div className="pattern-bars">
        {data.weekdays.map((w) => (
          <div key={w.weekday} className="pattern-row">
            <span className="pattern-label">{w.label.slice(0, 3)}</span>
            <div className="pattern-bar-track">
              <div className="pattern-bar-fill" style={{ width: `${(w.average_kg_co2e / max) * 100}%` }} />
            </div>
            <span className="pattern-value">{w.average_kg_co2e}kg</span>
            <span className="muted">({w.days_sampled}d)</span>
          </div>
        ))}
      </div>
    </div>
  );
}
