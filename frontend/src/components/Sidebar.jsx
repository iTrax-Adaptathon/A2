const SECTIONS = [
  { id: "dashboard", label: "Dashboard", icon: "📊" },
  { id: "log", label: "Log a day", icon: "✍️" },
  { id: "insights", label: "AI Analyst", icon: "🤖" },
  { id: "whatif", label: "What-If", icon: "🎲" },
  { id: "optimize", label: "Optimize", icon: "🎯" },
  { id: "budget", label: "Budget", icon: "💰" },
  { id: "roadmap", label: "Roadmap", icon: "🗺️" },
];

export default function Sidebar({ active, onSelect }) {
  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark">{"🔥"}</span>
        <div>
          <div className="sidebar-brand-title">Carbon Emission</div>
          <div className="sidebar-brand-sub">ADAPTATHON · SPRINT 1</div>
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
              <span className="nav-icon">{s.icon}</span>
              {s.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
