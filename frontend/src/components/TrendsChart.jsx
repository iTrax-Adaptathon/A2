import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = {
  commute: "#d4af37",
  food: "#f0e6c8",
  energy: "#c98a3e",
  flights: "#b8323a",
  shopping: "#c7c9cc",
  forecast: "#8d8b85",
};
const CATEGORIES = ["commute", "food", "energy", "flights", "shopping"];

const SOURCE_LABEL = {
  observed: "observed",
  inferred: "inferred",
  personal_estimate: "your average",
  population_default: "default",
};

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;

  if (row.isForecast) {
    return (
      <div className="chart-tooltip">
        <strong>{label} (forecast)</strong>
        <div className="tooltip-row">
          <span>projected</span>
          <span>{row.projected.toFixed(2)} kg</span>
        </div>
        <div className="tooltip-row">
          <span>range</span>
          <span>
            {row.low.toFixed(2)}&ndash;{row.high.toFixed(2)} kg
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      {CATEGORIES.filter((cat) => row[cat] > 0 || row[`${cat}_source`] !== "population_default").map((cat) => (
        <div key={cat} className="tooltip-row">
          <span style={{ color: COLORS[cat] }}>{cat}</span>
          <span>
            {row[cat].toFixed(2)} kg <em className={`source source-${row[`${cat}_source`]}`}>({SOURCE_LABEL[row[`${cat}_source`]]})</em>
          </span>
        </div>
      ))}
      <div className="tooltip-row tooltip-total">
        <span>total</span>
        <span>
          {row.total.toFixed(2)} kg <span className="tooltip-range">({row.totalLow?.toFixed(1)}&ndash;{row.totalHigh?.toFixed(1)})</span>
        </span>
      </div>
    </div>
  );
}

export default function TrendsChart({ trend, forecast }) {
  if (!trend?.length) {
    return (
      <div className="card">
        <h2>Trend &amp; forecast</h2>
        <p className="hint">Your footprint over time will show up here once you've logged a day or two.</p>
      </div>
    );
  }

  const history = trend.map((entry) => ({
    date: entry.date.slice(5),
    commute: entry.commute.kg_co2e,
    commute_source: entry.commute.source,
    food: entry.food.kg_co2e,
    food_source: entry.food.source,
    energy: entry.energy.kg_co2e,
    energy_source: entry.energy.source,
    flights: entry.flights.kg_co2e,
    flights_source: entry.flights.source,
    shopping: entry.shopping.kg_co2e,
    shopping_source: entry.shopping.source,
    total: entry.total_kg_co2e,
    totalLow: entry.total_low_kg_co2e,
    totalHigh: entry.total_high_kg_co2e,
    isForecast: false,
  }));

  const forecastRows = (forecast?.points || []).map((p) => ({
    date: p.date.slice(5),
    projected: p.projected_kg_co2e,
    low: p.low_kg_co2e,
    high: p.high_kg_co2e,
    forecastBand: [p.low_kg_co2e, p.high_kg_co2e],
    isForecast: true,
  }));

  const data = [...history, ...forecastRows];

  return (
    <div className="card">
      <h2>Trend &amp; forecast</h2>
      <p className="hint">
        Solid bars are logged days; the shaded band past the last bar is a {forecast?.method === "linear_regression" ? "regression-based" : "flat-average"} projection.
        A flight day can dwarf the rest of the bars &mdash; that's accurate, not a bug.
      </p>
      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
          <XAxis dataKey="date" fontSize={12} />
          <YAxis fontSize={12} label={{ value: "kg CO2e", angle: -90, position: "insideLeft" }} />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar dataKey="commute" stackId="a" fill={COLORS.commute} name="Commute" />
          <Bar dataKey="food" stackId="a" fill={COLORS.food} name="Food" />
          <Bar dataKey="energy" stackId="a" fill={COLORS.energy} name="Energy" />
          <Bar dataKey="flights" stackId="a" fill={COLORS.flights} name="Flights" />
          <Bar dataKey="shopping" stackId="a" fill={COLORS.shopping} radius={[4, 4, 0, 0]} name="Shopping" />
          <Area
            dataKey="forecastBand"
            fill={COLORS.forecast}
            stroke="none"
            fillOpacity={0.25}
            name="Forecast range"
            connectNulls
          />
          <Line
            dataKey="projected"
            stroke={COLORS.forecast}
            strokeDasharray="5 4"
            dot={{ r: 3 }}
            name="Forecast"
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
