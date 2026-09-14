import { useEffect, useState } from "react";
import { getInsights } from "../api";

const ICON = { info: "ℹ️", positive: "✅", warning: "⚠️" };

export default function InsightsFeed({ region, refreshKey }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getInsights(region)
      .then(setData)
      .finally(() => setLoading(false));
  }, [region, refreshKey]);

  return (
    <div className="card">
      <div className="section-header">
        <h2>AI Carbon Analyst</h2>
        <span className="pill">rule-based engine</span>
      </div>
      <p className="hint">
        Reads your trend, forecast, and optimization data and narrates what matters — no
        external API call required. Swapping this for an LLM-backed analyst is a one-file change
        (<code>backend/app/insights.py</code>).
      </p>

      {loading && <p className="hint">Analyzing...</p>}

      {!loading && data && (
        <ul className="insight-feed">
          {data.insights.map((insight, i) => (
            <li key={i} className={`insight-item insight-${insight.severity}`}>
              <span className="insight-icon">{ICON[insight.severity]}</span>
              <div>
                <strong>{insight.headline}</strong>
                <p>{insight.detail}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
