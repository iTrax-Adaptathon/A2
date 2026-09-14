const MODULES = [
  {
    icon: "🪞",
    title: "Carbon Digital Twin",
    detail:
      "A live simulated model of your household/commute that reacts as you log — e.g. an animated home whose 'emissions glow' dims as you shift habits.",
  },
  {
    icon: "🧩",
    title: "Smart missing-data reconstruction (advanced)",
    detail:
      "Today's gap-filling uses a flat personal average (see 'Your average' badges). A fuller version would model day-of-week and seasonal patterns — e.g. knowing your Saturday footprint looks different from a Tuesday.",
  },
  {
    icon: "🚨",
    title: "Carbon anomaly detection",
    detail:
      "Flag days that break your normal pattern (a huge energy spike, an unusually long commute) automatically, instead of relying on the analyst's window comparison.",
  },
  {
    icon: "📊",
    title: "Behavioral pattern analysis",
    detail: "Surface recurring patterns — 'you drive 40% more on Mondays' — mined from logging history over time.",
  },
  {
    icon: "🏆",
    title: "Carbon ROI ranking",
    detail:
      "The optimizer already ranks actions by kg saved/day. A full ROI ranking would weigh that against real-world cost/effort to save per rupee spent, not just per lever pulled.",
  },
  {
    icon: "🎯",
    title: "Personalized carbon budget",
    detail:
      "The optimizer takes an ad-hoc target today. A persisted budget would track progress against it over weeks, with streaks and alerts when you're trending over.",
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
        These modules aren't wired up yet in this Sprint 1 build — shown here so whoever
        inherits this codebase knows what's scoped next and why it isn't live.
      </p>
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
