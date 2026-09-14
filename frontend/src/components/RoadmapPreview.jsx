const SHIPPED = [
  { title: "Smart missing-data reconstruction", detail: "now weekday-aware -- see 'Tue avg' style badges" },
  { title: "Carbon anomaly detection", detail: "median/MAD-based, on the Dashboard and in the AI Analyst" },
  { title: "Behavioral pattern analysis", detail: "weekday breakdown, on the Dashboard and in the AI Analyst" },
  { title: "Personalized carbon budget", detail: "persisted target + streak tracking, its own Budget tab" },
];

const MODULES = [
  {
    icon: "🪞",
    title: "Carbon Digital Twin",
    detail:
      "A live simulated model of your household/commute that reacts as you log — e.g. an animated home whose 'emissions glow' dims as you shift habits.",
  },
  {
    icon: "🏆",
    title: "Carbon ROI ranking",
    detail:
      "The optimizer already ranks actions by kg saved/day. A full ROI ranking would weigh that against real-world cost/effort to save per rupee spent, not just per lever pulled.",
  },
  {
    icon: "🧪",
    title: "Carbon experiments",
    detail:
      "Structured A/B-style trials — e.g. 'meatless Mondays for 2 weeks' — that measure before/after impact using the same estimator.",
  },
];

export default function RoadmapPreview() {
  return (
    <div className="card">
      <div className="section-header">
        <h2>Roadmap</h2>
        <span className="pill">preview — Sprint 2</span>
      </div>
      <p className="hint">
        These modules aren't wired up yet in this build — shown here so whoever inherits this
        codebase knows what's scoped next and why it isn't live.
      </p>

      <div className="shipped-list">
        <strong>Shipped since the first pass:</strong>
        <ul>
          {SHIPPED.map((s) => (
            <li key={s.title}>
              <span className="badge badge-observed">Built</span> {s.title}{" "}
              <span className="muted">&mdash; {s.detail}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="roadmap-grid">
        {MODULES.map((m) => (
          <div key={m.title} className="roadmap-card">
            <span className="roadmap-icon">{m.icon}</span>
            <h3>{m.title}</h3>
            <p>{m.detail}</p>
            <span className="badge badge-preview">Preview</span>
          </div>
        ))}
      </div>
    </div>
  );
}
