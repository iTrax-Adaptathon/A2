import { useState } from "react";
import { upsertLog } from "../api";

const todayIso = () => new Date().toISOString().slice(0, 10);

export default function LogForm({ reference, region, onSaved }) {
  const [date, setDate] = useState(todayIso());
  const [commuteMode, setCommuteMode] = useState("");
  const [commuteDistance, setCommuteDistance] = useState("");
  const [dietType, setDietType] = useState("");
  const [energyMode, setEnergyMode] = useState("level"); // "level" | "kwh"
  const [energyKwh, setEnergyKwh] = useState("");
  const [energyLevel, setEnergyLevel] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const needsDistance = commuteMode && commuteMode !== "wfh" && commuteMode !== "walk" && commuteMode !== "cycle";

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await upsertLog({
        date,
        commute_mode: commuteMode || null,
        commute_distance_km:
          commuteMode && commuteMode !== "wfh" ? Number(commuteDistance) || (needsDistance ? null : 0) : null,
        diet_type: dietType || null,
        energy_kwh: energyMode === "kwh" && energyKwh !== "" ? Number(energyKwh) : null,
        energy_level: energyMode === "level" ? energyLevel || null : null,
        notes: notes || null,
        region,
        channel: "form",
        inferred_fields: [],
      });
      onSaved();
      setNotes("");
    } catch (err) {
      setError(err?.response?.data?.detail ? JSON.stringify(err.response.data.detail) : "Failed to save log.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="log-form" onSubmit={handleSubmit}>
      <p className="hint">
        Leave anything blank if you don't know it or forgot to track it &mdash; the estimator will fill
        the gap using your own recent average instead of assuming zero.
      </p>

      <label>
        Date
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
      </label>

      <fieldset>
        <legend>Commute</legend>
        <label>
          Mode
          <select value={commuteMode} onChange={(e) => setCommuteMode(e.target.value)}>
            <option value="">Not logged</option>
            {reference.commute_modes.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        {needsDistance && (
          <label>
            Distance (km)
            <input
              type="number"
              min="0"
              step="0.1"
              value={commuteDistance}
              onChange={(e) => setCommuteDistance(e.target.value)}
              placeholder="e.g. 12"
            />
          </label>
        )}
      </fieldset>

      <fieldset>
        <legend>Food</legend>
        <label>
          Overall diet today
          <select value={dietType} onChange={(e) => setDietType(e.target.value)}>
            <option value="">Not logged</option>
            {reference.diet_types.map((d) => (
              <option key={d} value={d}>
                {d.replace("_", " ")}
              </option>
            ))}
          </select>
        </label>
      </fieldset>

      <fieldset>
        <legend>Energy</legend>
        <div className="radio-row">
          <label className="inline">
            <input
              type="radio"
              checked={energyMode === "level"}
              onChange={() => setEnergyMode("level")}
            />
            Rough level
          </label>
          <label className="inline">
            <input type="radio" checked={energyMode === "kwh"} onChange={() => setEnergyMode("kwh")} />
            Exact kWh
          </label>
        </div>
        {energyMode === "level" ? (
          <select value={energyLevel} onChange={(e) => setEnergyLevel(e.target.value)}>
            <option value="">Not logged</option>
            {reference.energy_levels.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        ) : (
          <input
            type="number"
            min="0"
            step="0.1"
            value={energyKwh}
            onChange={(e) => setEnergyKwh(e.target.value)}
            placeholder="e.g. 6.5"
          />
        )}
      </fieldset>

      <label>
        Notes (optional)
        <input type="text" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Anything unusual today?" />
      </label>

      {error && <p className="error">{error}</p>}

      <button type="submit" disabled={saving}>
        {saving ? "Saving..." : "Save day"}
      </button>
    </form>
  );
}
