import { TelemetryRecord, AnalyticsSummary, DispatchPlan, AuditEvent, Asset } from "../types";

const BASE_URL = "/api";

export async function fetchHealth(): Promise<any> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function fetchTelemetryHistory(limit: number = 96): Promise<TelemetryRecord[]> {
  const res = await fetch(`${BASE_URL}/telemetry/history?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch telemetry history");
  const data = await res.json();
  return data.data;
}

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  const res = await fetch(`${BASE_URL}/analytics/summary`);
  if (!res.ok) throw new Error("Failed to fetch analytics summary");
  return res.json();
}

export async function fetchAssets(): Promise<Asset[]> {
  const res = await fetch(`${BASE_URL}/assets`);
  if (!res.ok) throw new Error("Failed to fetch assets");
  return res.json();
}

export async function fetchTariffs(): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/tariffs`);
  if (!res.ok) throw new Error("Failed to fetch tariffs");
  return res.json();
}

export async function fetchCarbon(): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/carbon`);
  if (!res.ok) throw new Error("Failed to fetch carbon");
  return res.json();
}

export async function fetchAuditLogs(limit: number = 50): Promise<AuditEvent[]> {
  const res = await fetch(`${BASE_URL}/audit-logs?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch audit logs");
  const data = await res.json();
  return data.data;
}

export async function fetchExperiments(): Promise<any> {
  const res = await fetch(`${BASE_URL}/experiments`);
  if (!res.ok) throw new Error("Failed to fetch experiments");
  return res.json();
}

export async function planDispatch(params: {
  scenario: string;
  controller: string;
  risk_mode: string;
  carbon_weight: number;
  emissions_budget_kg?: number;
}): Promise<DispatchPlan> {
  const res = await fetch(`${BASE_URL}/dispatch/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error("Failed to generate dispatch plan");
  return res.json();
}

export async function submitManualOverride(payload: {
  idempotency_key: string;
  actor: string;
  hvac_cooling_thermal_kw: number;
  battery_charge_kw: number;
  battery_discharge_kw: number;
  reason: string;
  duration_minutes: number;
}): Promise<any> {
  const res = await fetch(`${BASE_URL}/dispatch/override`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.error ? JSON.stringify(errorData.error) : "Failed to apply override");
  }
  return res.json();
}
