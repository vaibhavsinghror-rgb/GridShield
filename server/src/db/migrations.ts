export const MIGRATIONS = [
  `
  CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    capacity_val REAL NOT NULL,
    capacity_unit TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  `,
  `
  CREATE TABLE IF NOT EXISTS simulation_runs (
    id TEXT PRIMARY KEY,
    scenario TEXT NOT NULL,
    controller TEXT NOT NULL,
    seed INTEGER NOT NULL,
    total_cost_usd REAL,
    total_emissions_kg REAL,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  `,
  `
  CREATE TABLE IF NOT EXISTS telemetry_records (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step INTEGER NOT NULL,
    time_hours REAL NOT NULL,
    indoor_temp_c REAL NOT NULL,
    outdoor_temp_c REAL NOT NULL,
    solar_generation_kw REAL NOT NULL,
    base_demand_kw REAL NOT NULL,
    hvac_electric_kw REAL NOT NULL,
    battery_charge_kw REAL NOT NULL,
    battery_discharge_kw REAL NOT NULL,
    grid_power_kw REAL NOT NULL,
    electricity_cost REAL NOT NULL,
    operational_emissions_kg REAL NOT NULL,
    comfort_violation_deg REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(run_id) REFERENCES simulation_runs(id) ON DELETE CASCADE,
    UNIQUE(run_id, step)
  );
  CREATE INDEX IF NOT EXISTS idx_telemetry_run_step ON telemetry_records(run_id, step);
  `,
  `
  CREATE TABLE IF NOT EXISTS battery_states (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step INTEGER NOT NULL,
    soc REAL NOT NULL,
    energy_kwh REAL NOT NULL,
    degradation_cost REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(run_id) REFERENCES simulation_runs(id) ON DELETE CASCADE
  );
  `,
  `
  CREATE TABLE IF NOT EXISTS tariff_observations (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step INTEGER NOT NULL,
    hour_of_day REAL NOT NULL,
    rate_per_kwh REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  `,
  `
  CREATE TABLE IF NOT EXISTS carbon_observations (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step INTEGER NOT NULL,
    intensity_gco2_per_kwh REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  `,
  `
  CREATE TABLE IF NOT EXISTS dispatch_schedules (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    controller TEXT NOT NULL,
    risk_mode TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    explanation_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  `,
  `
  CREATE TABLE IF NOT EXISTS manual_overrides (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT UNIQUE NOT NULL,
    actor TEXT NOT NULL,
    hvac_cooling_thermal_kw REAL NOT NULL,
    battery_charge_kw REAL NOT NULL,
    battery_discharge_kw REAL NOT NULL,
    reason TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  CREATE INDEX IF NOT EXISTS idx_overrides_idempotency ON manual_overrides(idempotency_key);
  `,
  `
  CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    before_state TEXT,
    after_state TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at);
  `,
  `
  CREATE TABLE IF NOT EXISTS experiment_summaries (
    id TEXT PRIMARY KEY,
    experiment_name TEXT NOT NULL,
    scenario TEXT NOT NULL,
    controller TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  `
];
