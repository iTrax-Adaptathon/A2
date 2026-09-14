import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { getReference, getSummary } from "./api";
import HistoryTable from "./components/HistoryTable";
import LogForm from "./components/LogForm";
import SummaryCards from "./components/SummaryCards";
import TrendsChart from "./components/TrendsChart";

function App() {
  const [reference, setReference] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const s = await getSummary();
      setSummary(s);
      setError(null);
    } catch {
      setError("Can't reach the backend. Is it running on port 8000?");
    }
  }, []);

  useEffect(() => {
    getReference()
      .then(setReference)
      .catch(() => setError("Can't reach the backend. Is it running on port 8000?"));
    refresh();
  }, [refresh]);

  return (
    <div className="app-shell">
      <header>
        <h1>Carbon Footprint Tracker</h1>
        <p className="subtitle">Adaptathon &middot; Sprint 1 &middot; Q2</p>
      </header>

      {error && <div className="card error-banner">{error}</div>}

      {reference && (
        <main>
          <LogForm reference={reference} onSaved={refresh} />
          <div className="right-col">
            <SummaryCards summary={summary} />
            <TrendsChart trend={summary?.trend} />
            <HistoryTable trend={summary?.trend} onChanged={refresh} />
          </div>
        </main>
      )}
    </div>
  );
}

export default App;
