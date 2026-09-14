const LABELS = {
  observed: "Observed",
  inferred: "Inferred",
  personal_estimate: "Your average",
  population_default: "Default",
};

const BASIS_LABELS = {
  weekday_average: "weekday-matched",
  rolling_average: "flat",
};

export default function SourceBadge({ source, uncertaintyPct, basis }) {
  if (!source) return null;
  return (
    <span className={`badge badge-${source}`} title={basis ? `${BASIS_LABELS[basis]} personal average` : undefined}>
      {LABELS[source] || source}
      {basis && <span className="badge-pct"> ({basis === "weekday_average" ? "weekday" : "flat"})</span>}
      {typeof uncertaintyPct === "number" && <span className="badge-pct"> &plusmn;{Math.round(uncertaintyPct * 100)}%</span>}
    </span>
  );
}
