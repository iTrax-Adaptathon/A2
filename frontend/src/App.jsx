import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { getForecast, getReference, getRegions, getSummary } from "./api";
import AnomaliesCard from "./components/AnomaliesCard";
import BudgetPanel from "./components/BudgetPanel";
import HistoryTable from "./components/HistoryTable";
import InsightsFeed from "./components/InsightsFeed";
import LogPanel from "./components/LogPanel";
import OptimizerPanel from "./components/OptimizerPanel";
import PatternsCard from "./components/PatternsCard";
import RoadmapPreview from "./components/RoadmapPreview";
import Sidebar from "./components/Sidebar";
import SummaryCards from "./components/SummaryCards";
import TopBar from "./components/TopBar";
import TrendsChart from "./components/TrendsChart";
import WhatIfSimulator from "./components/WhatIfSimulator";
import { RegionProvider, useRegion } from "./RegionContext";

const SECTION_TITLES = {
  dashboard: "Dashboard",
  log: "Log a day",
  insights: "AI Carbon Analyst",
  whatif: "What-If Simulator",
  optimize: "Carbon Budget Optimizer",
  budget: "Carbon Budget",
  roadmap: "Roadmap",
};

function Dashboard({ reference }) {
  const { region } = useRegion();
  const [summary, setSummary] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    Promise.all([getSummary(), getForecast(7)])
      .then(([s, f]) => {
        setSummary(s);
        setForecast(f);
        setError(null);
      })
      .catch(() => setError("Can't reach the backend. Is it running on port 8000?"));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh, region, refreshKey]);

  if (error) return <div className="card error-banner">{error}</div>;

  const mixedRegions = summary?.trend?.some((t) => t.region !== region);

  return (
    <>
      {mixedRegions && (
        <div className="card region-note">
          Some logged days used a different region's factors than {region} is currently set to.
          That's intentional — versioned regional factors mean a day's footprint is computed
          with whatever profile was active when it was logged, not silently restated later.
        </div>
      )}
      <SummaryCards summary={summary} />
      <TrendsChart trend={summary?.trend} forecast={forecast} />
      <PatternsCard refreshKey={refreshKey} />
      <AnomaliesCard refreshKey={refreshKey} />
      <HistoryTable trend={summary?.trend} onChanged={() => setRefreshKey((k) => k + 1)} />
    </>
  );
}

function LogSection({ reference }) {
  const { region } = useRegion();
  const [, setTick] = useState(0);
  return <LogPanel reference={reference} region={region} onSaved={() => setTick((t) => t + 1)} />;
}

function AppShell({ reference }) {
  const [section, setSection] = useState("dashboard");
  const { region } = useRegion();
  const [summaryForOptimizer, setSummaryForOptimizer] = useState(null);

  useEffect(() => {
    if (section === "optimize" || section === "budget") {
      getSummary().then(setSummaryForOptimizer);
    }
  }, [section, region]);

  return (
    <div className="app-shell">
      <Sidebar active={section} onSelect={setSection} />
      <div className="app-main">
        <TopBar title={SECTION_TITLES[section]} />
        <main>
          {section === "dashboard" && <Dashboard reference={reference} />}
          {section === "log" && <LogSection reference={reference} />}
          {section === "insights" && <InsightsFeed region={region} refreshKey={section} />}
          {section === "whatif" && <WhatIfSimulator reference={reference} region={region} />}
          {section === "optimize" && <OptimizerPanel region={region} summary={summaryForOptimizer} />}
          {section === "budget" && <BudgetPanel summary={summaryForOptimizer} />}
          {section === "roadmap" && <RoadmapPreview />}
        </main>
      </div>
    </div>
  );
}

function App() {
  const [reference, setReference] = useState(null);
  const [regions, setRegions] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([getReference(), getRegions()])
      .then(([ref, regs]) => {
        setReference(ref);
        setRegions(regs);
      })
      .catch(() => setError("Can't reach the backend. Is it running on port 8000?"));
  }, []);

  if (error) {
    return (
      <div className="app-shell">
        <div className="card error-banner">{error}</div>
      </div>
    );
  }

  if (!reference || !regions) return null;

  return (
    <RegionProvider regions={regions}>
      <AppShell reference={reference} />
    </RegionProvider>
  );
}

export default App;
