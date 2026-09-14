export default function SummaryCards({ summary }) {
  if (!summary || summary.days_logged === 0) {
    return (
      <div className="card">
        <p className="hint">No days logged yet. Add your first entry to see your footprint.</p>
      </div>
    );
  }

  const { average_kg_co2e_per_day, category_totals, days_logged, trend } = summary;
  const biggest = Object.entries(category_totals).sort((a, b) => b[1] - a[1])[0];

  const totalLow = trend.reduce((sum, t) => sum + t.total_low_kg_co2e, 0);
  const totalHigh = trend.reduce((sum, t) => sum + t.total_high_kg_co2e, 0);
  const avgLow = round1(totalLow / days_logged);
  const avgHigh = round1(totalHigh / days_logged);

  return (
    <div className="card summary-cards">
      <div className="stat">
        <span className="stat-value">{average_kg_co2e_per_day}</span>
        <span className="stat-label">kg CO2e / day (avg)</span>
        <span className="stat-sub">
          {avgLow}&ndash;{avgHigh} kg range
        </span>
      </div>
      <div className="stat">
        <span className="stat-value">{days_logged}</span>
        <span className="stat-label">days logged</span>
      </div>
      <div className="stat">
        <span className="stat-value stat-highlight">{biggest[0]}</span>
        <span className="stat-label">biggest contributor</span>
      </div>
      <div className="category-breakdown">
        {Object.entries(category_totals).map(([cat, kg]) => (
          <div key={cat} className="category-row">
            <span>{cat}</span>
            <span>{kg} kg</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function round1(n) {
  return Math.round(n * 10) / 10;
}
