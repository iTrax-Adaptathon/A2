import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const client = axios.create({ baseURL: API_BASE });

export const getReference = () => client.get("/api/reference").then((r) => r.data);
export const getRegions = () => client.get("/api/regions").then((r) => r.data);

export const listLogs = () => client.get("/api/logs").then((r) => r.data);
export const getSummary = () => client.get("/api/summary").then((r) => r.data);
export const upsertLog = (entry) => client.post("/api/logs", entry).then((r) => r.data);
export const deleteLog = (date) => client.delete(`/api/logs/${date}`).then((r) => r.data);

export const parseLogText = (text, channel, region) =>
  client.post("/api/logs/parse", { text, channel, region }).then((r) => r.data);

export const simulate = (payload) => client.post("/api/simulate", payload).then((r) => r.data);

export const getForecast = (days = 7) =>
  client.get("/api/forecast", { params: { days } }).then((r) => r.data);

export const optimize = (target_kg_per_day, region) =>
  client.post("/api/optimize", { target_kg_per_day, region }).then((r) => r.data);

export const getInsights = (region) =>
  client.get("/api/insights", { params: { region } }).then((r) => r.data);

export const getAnomalies = () => client.get("/api/anomalies").then((r) => r.data);

export const getPatterns = () => client.get("/api/patterns").then((r) => r.data);

export const getBudget = () => client.get("/api/budget").then((r) => r.data);
export const setBudget = (target_kg_per_day) =>
  client.post("/api/budget", { target_kg_per_day }).then((r) => r.data);
export const clearBudget = () => client.delete("/api/budget").then((r) => r.data);
export const getBudgetStatus = () => client.get("/api/budget/status").then((r) => r.data);
