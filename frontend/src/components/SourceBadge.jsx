const LABELS = {
  observed: "Observed",
  inferred: "Inferred",
  personal_estimate: "Your average",
  population_default: "Default",
};

export default function SourceBadge({ source, uncertaintyPct }) {
  if (!source) return null;
  return (
    <span className={`badge badge-${source}`}>
      {LABELS[source] || source}
      {typeof uncertaintyPct === "number" && <span className="badge-pct"> &plusmn;{Math.round(uncertaintyPct * 100)}%</span>}
    </span>
  );
}
