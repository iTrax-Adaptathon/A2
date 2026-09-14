import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const client = axios.create({ baseURL: API_BASE });

export const getReference = () => client.get("/api/reference").then((r) => r.data);
export const listLogs = () => client.get("/api/logs").then((r) => r.data);
export const getSummary = () => client.get("/api/summary").then((r) => r.data);
export const upsertLog = (entry) => client.post("/api/logs", entry).then((r) => r.data);
export const deleteLog = (date) => client.delete(`/api/logs/${date}`).then((r) => r.data);
