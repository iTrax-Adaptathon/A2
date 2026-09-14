import { createContext, useContext, useEffect, useState } from "react";

const RegionContext = createContext(null);

export function RegionProvider({ regions, children }) {
  const [region, setRegion] = useState(() => {
    try {
      return localStorage.getItem("carbon_region") || "IN";
    } catch {
      return "IN";
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("carbon_region", region);
    } catch {
      // ignore -- private browsing / storage disabled, not critical
    }
  }, [region]);

  const activeRegion = regions.find((r) => r.code === region) || regions[0];

  return (
    <RegionContext.Provider value={{ region, setRegion, regions, activeRegion }}>
      {children}
    </RegionContext.Provider>
  );
}

export function useRegion() {
  const ctx = useContext(RegionContext);
  if (!ctx) throw new Error("useRegion must be used inside a RegionProvider");
  return ctx;
}
