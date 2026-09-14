import { useEffect, useState } from "react";
import { simulate } from "../api";
import SourceBadge from "./SourceBadge";

export default function WhatIfSimulator({ reference, region }) {
  const [commuteMode, setCommuteMode] = useState("car");
  const [commuteDistance, setCommuteDistance] = useState(12);
  const [dietType, setDietType] = useState("average");
  const [energyLevel, setEnergyLevel] = useState("medium");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const handle = setTimeout(() => {
      simulate({
        commute_mode: commuteMode || null,
        commute_distance_km: commuteMode && commuteMode !== "wfh" ? Number(commuteDistance) : commuteMode === "wfh" ? 0 : null,
        diet_type: dietType || null,
        energy_level: energyLevel || null,
        region,
      })
        .then((r) => {
          if (!cancelled) setResult(r);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [commuteMode, commuteDistance, dietType, energyLevel, region]);

  const needsDistance = commuteMode && commuteMode !== "wfh";

  return (
    <div className="card whatif">
      <div className="section-header">
        <h2>What-if simulator</h2>
        <span className="pill">live, not saved</span>
      </div>
      <p className="hint">Try a hypothetical day and see the projected footprint instantly — nothing here is logged.</p>

      <div className="whatif-grid">
        <div className="whatif-controls">
          <label>
            Commute mode
            <select value={commuteMode} onChange={(e) => setCommuteMode(e.target.value)}>
              {reference.commute_modes.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          {needsDistance && (
            <label>
              Distance: {commuteDistance}km
              <input
                type="range"
                min="0"
                max="60"
                value={commuteDistance}
                onChange={(e) => setCommuteDistance(e.target.value)}
              />
            </label>
          )}
          <label>
            Diet
            <select value={dietType} onChange={(e) => setDietType(e.target.value)}>
              {reference.diet_types.map((d) => (
                <option key={d} value={d}>
                  {d.replace("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label>
            Energy usage
            <select value={energyLevel} onChange={(e) => setEnergyLevel(e.target.value)}>
              {reference.energy_levels.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="whatif-result">
          {result ? (
            <>
              <div className="whatif-total" style={{ opacity: loading ? 0.5 : 1 }}>
                <span className="stat-value">{result.total_kg_co2e}</span>
                <span className="stat-label">kg CO2e for this scenario</span>
              </div>
              {result.delta_kg_co2e != null && (
                <p className={`whatif-delta ${result.delta_kg_co2e <= 0 ? "positive" : "warning"}`}>
                  {result.delta_kg_co2e <= 0 ? "↓" : "↑"} {Math.abs(result.delta_kg_co2e)}kg vs. your most recent
                  logged day ({result.baseline_kg_co2e}kg)
                </p>
              )}
              <ul className="whatif-breakdown">
                <li>
                  Commute: {result.commute.kg_co2e}kg <SourceBadge source={result.commute.source} />
                </li>
                <li>
                  Food: {result.food.kg_co2e}kg <SourceBadge source={result.food.source} />
                </li>
                <li>
                  Energy: {result.energy.kg_co2e}kg <SourceBadge source={result.energy.source} />
                </li>
              </ul>
            </>
          ) : (
            <p className="hint">Computing...</p>
          )}
        </div>
      </div>
    </div>
  );
}
