import { useState } from "react";
import LogForm from "./LogForm";
import TextChannelLogger from "./TextChannelLogger";

const TABS = [
  { id: "form", label: "Form" },
  { id: "natural_language", label: "Natural language" },
  { id: "voice", label: "Voice" },
  { id: "receipt", label: "Receipt" },
];

export default function LogPanel({ reference, region, onSaved }) {
  const [tab, setTab] = useState("form");

  return (
    <div className="card log-panel">
      <h2>Log a day</h2>
      <div className="tab-row" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            className={`tab-button ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
            type="button"
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "form" && <LogForm reference={reference} region={region} onSaved={onSaved} />}
      {tab !== "form" && <TextChannelLogger channel={tab} region={region} onSaved={onSaved} />}
    </div>
  );
}
