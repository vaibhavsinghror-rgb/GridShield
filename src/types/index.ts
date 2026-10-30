export interface TelemetryRecord {
  id: string;
  run_id: string;
  step: number;
  time_hours: number;
  indoor_temp_c: number;
  outdoor_temp_c: number;
  solar_generation_kw: number;
  base_demand_kw: number;
  hvac_electric_kw: number;
  battery_charge_kw: number;
  battery_discharge_kw: number;
  grid_power_kw: number;
  electricity_cost: number;
  operational_emissions_kg: number;
  comfort_violation_deg: number;
  created_at: string;
}

export interface AnalyticsSummary {
  total_steps: number;
  today_electricity_cost_usd: number;
  today_emissions_kg: number;
  peak_grid_kw: number;
  comfort_violation_deg_hours: number;
  avg_indoor_temp_c: number;
  baseline_comparison: {
    baseline_name: string;
    baseline_cost_usd: number;
    savings_usd: number;
    savings_pct: number;
  };
}

export interface DispatchPlan {
  scenario: string;
  controller: string;
  risk_mode: string;
  carbon_weight: number;
  emissions_budget_kg: number | null;
  horizon_steps: number;
  summary: {
    expected_cost_usd: number;
    expected_emissions_kg: number;
    battery_throughput_kwh: number;
    comfort_risk_deg_hours: number;
  };
  schedule: Array<{
    step: number;
    time_hours: number;
    hour_of_day: number;
    hvac_cooling_thermal_kw: number;
    battery_charge_kw: number;
    battery_discharge_kw: number;
    predicted_grid_kw: number;
  }>;
}

export interface AuditEvent {
  id: string;
  actor: string;
  action: string;
  reason: string;
  before_state: string;
  after_state: string;
  created_at: string;
}

export interface Asset {
  id: string;
  name: string;
  asset_type: string;
  capacity_val: number;
  capacity_unit: string;
  status: string;
}
