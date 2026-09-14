import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = { commute: "#6366f1", food: "#22c55e", energy: "#f59e0b" };

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      {["commute", "food", "energy"].map((cat) => (
        <div key={cat} className="tooltip-row">
          <span style={{ color: COLORS[cat] }}>{cat}</span>
          <span>
            {row[cat].toFixed(2)} kg{" "}
            <em className={`source source-${row[`${cat}_source`]}`}>({row[`${cat}_source`]})</em>
          </span>
        </div>
      ))}
      <div className="tooltip-row tooltip-total">
        <span>total</span>
        <span>{row.total.toFixed(2)} kg</span>
      </div>
    </div>
  );
}

export default function TrendsChart({ trend }) {
  if (!trend?.length) {
    return (
      <div className="card">
        <h2>Trend</h2>
        <p className="hint">Your footprint over time will show up here once you've logged a day or two.</p>
      </div>
    );
  }

  const data = trend.map((entry) => ({
    date: entry.date.slice(5), // MM-DD, compact for the axis
    commute: entry.commute.kg_co2e,
    commute_source: entry.commute.source,
    food: entry.food.kg_co2e,
    food_source: entry.food.source,
    energy: entry.energy.kg_co2e,
    energy_source: entry.energy.source,
    total: entry.total_kg_co2e,
  }));

  return (
    <div className="card">
      <h2>Trend</h2>
      <p className="hint">
        Solid segments are things you logged; hover a bar to see which parts were estimated from your
        own average.
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
          <XAxis dataKey="date" fontSize={12} />
          <YAxis fontSize={12} label={{ value: "kg CO2e", angle: -90, position: "insideLeft" }} />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar dataKey="commute" stackId="a" fill={COLORS.commute} />
          <Bar dataKey="food" stackId="a" fill={COLORS.food} />
          <Bar dataKey="energy" stackId="a" fill={COLORS.energy} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
