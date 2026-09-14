const MODULES = [
  {
    title: "Carbon Digital Twin",
    detail:
      "A live simulated model of your household/commute that reacts as you log — e.g. an animated home whose 'emissions glow' dims as you shift habits.",
  },
  {
    title: "Carbon anomaly detection",
    detail:
      "Backend logic exists (median/MAD deviation, GET /api/anomalies) but isn't wired into the UI yet.",
  },
  {
    title: "Behavioral pattern analysis",
    detail:
      "Weekday breakdown endpoint (GET /api/patterns) is done; the dashboard visualization for it isn't.",
  },
  {
    title: "Carbon ROI ranking",
    detail:
      "The optimizer already ranks actions by kg saved/day. A full ROI ranking would weigh that against real-world cost/effort to save per rupee spent, not just per lever pulled.",
  },
  {
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
        <span className="pill">preview</span>
      </div>
      <p className="hint">
        Not wired up yet — some of this has backend logic already sitting there unused, some is
        just an idea.
      </p>

      <div className="roadmap-grid">
        {MODULES.map((m) => (
          <div key={m.title} className="roadmap-card">
            <h3>{m.title}</h3>
            <p>{m.detail}</p>
            <span className="badge badge-preview">Preview</span>
          </div>
        ))}
      </div>
    </div>
  );
}
