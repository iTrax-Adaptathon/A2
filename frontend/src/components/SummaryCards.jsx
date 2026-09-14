export default function SummaryCards({ summary }) {
  if (!summary || summary.days_logged === 0) {
    return (
      <div className="card">
        <p className="hint">No days logged yet. Add your first entry to see your footprint.</p>
      </div>
    );
  }

  const { average_kg_co2e_per_day, category_totals, days_logged } = summary;
  const biggest = Object.entries(category_totals).sort((a, b) => b[1] - a[1])[0];

  return (
    <div className="card summary-cards">
      <div className="stat">
        <span className="stat-value">{average_kg_co2e_per_day}</span>
        <span className="stat-label">kg CO2e / day (avg)</span>
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
