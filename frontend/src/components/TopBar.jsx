import { useRegion } from "../RegionContext";

export default function TopBar({ title }) {
  const { region, setRegion, regions, activeRegion } = useRegion();

  return (
    <header className="topbar">
      <h1>{title}</h1>
      <div className="topbar-right">
        <label className="region-select" title="Past entries keep the region+version active when they were logged (that's what 'versioned' means) — only new entries and live tools (What-If, Optimize) use this selection.">
          <span>Region</span>
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            {regions.map((r) => (
              <option key={r.code} value={r.code}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
        {activeRegion && <span className="pill">factors v{activeRegion.version}</span>}
      </div>
    </header>
  );
}
