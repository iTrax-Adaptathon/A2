import { useEffect, useState } from "react";
import { getAnomalies } from "../api";

export default function AnomaliesCard({ refreshKey }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    getAnomalies().then(setData);
  }, [refreshKey]);

  if (!data || data.anomalies.length === 0) return null;

  return (
    <div className="card">
      <div className="section-header">
        <h2>Anomalies</h2>
        <span className="pill">median/MAD detection</span>
      </div>
      <p className="hint">
        Days that broke from your normal pattern, flagged with a robust statistic (median +
        median-absolute-deviation) so one huge day doesn't hide itself in the average.
      </p>
      <ul className="anomaly-list">
        {[...data.anomalies].reverse().map((a) => (
          <li key={a.date} className={`anomaly-item anomaly-${a.direction}`}>
            <span className="anomaly-date">{a.date}</span>
            <span className="anomaly-z">z={a.modified_z_score}</span>
            <span className="anomaly-message">{a.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
