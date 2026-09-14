const SECTIONS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "log", label: "Log a day" },
  { id: "insights", label: "AI Analyst" },
  { id: "whatif", label: "What-If" },
  { id: "optimize", label: "Optimize" },
  { id: "budget", label: "Budget" },
  { id: "roadmap", label: "Roadmap" },
];

export default function Sidebar({ active, onSelect }) {
  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark">C</span>
        <div>
          <div className="sidebar-brand-title">Carbon Emission</div>
          <div className="sidebar-brand-sub">ADAPTATHON &middot; SPRINT 1</div>
        </div>
      </div>
      <ul>
        {SECTIONS.map((s) => (
          <li key={s.id}>
            <button
              type="button"
              className={active === s.id ? "active" : ""}
              onClick={() => onSelect(s.id)}
            >
              {s.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
