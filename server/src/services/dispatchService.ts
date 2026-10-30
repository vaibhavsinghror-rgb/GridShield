import { DatabaseSync } from "node:sqlite";
import crypto from "crypto";
import { getDatabase } from "../db/database.js";

export interface DispatchOverrideInput {
  idempotency_key: string;
  actor: string;
  hvac_cooling_thermal_kw: number;
  battery_charge_kw: number;
  battery_discharge_kw: number;
  reason: string;
  duration_minutes: number;
}

export class DispatchService {
  private db: DatabaseSync;

  constructor(db?: DatabaseSync) {
    this.db = db || getDatabase();
  }

  public getAuditLogs(limit: number = 50, offset: number = 0): any[] {
    return this.db.prepare(`
      SELECT * FROM audit_events
      ORDER BY created_at DESC
      LIMIT ? OFFSET ?
    `).all(limit, offset);
  }

  public getCurrentDispatch(): any {
    return {
      active_controller: "UCC-MPC",
      current_action: {
        hvac_cooling_thermal_kw: 12.5,
        hvac_heating_thermal_kw: 0.0,
        battery_charge_kw: 0.0,
        battery_discharge_kw: 15.0,
        ev_charge_kw: 0.0,
      },
      explanation: {
        reasoning: "Peak electricity tariff window ($0.32/kWh) and elevated carbon intensity active. Discharging BESS at 15.0 kW to eliminate grid import while modulating HVAC cooling to preserve 22.5°C comfort setpoint.",
        active_constraints: ["BESS discharge power limit (25 kW)", "Comfort band (21-24°C)"],
        risk_mode: "cvar",
        solver_status: "OPTIMAL",
      },
      timestamp: new Date().toISOString(),
    };
  }

  public planDispatch(params: {
    scenario: string;
    controller: string;
    risk_mode: string;
    carbon_weight: number;
    emissions_budget_kg?: number;
  }): any {
    const horizonSteps = 96;
    const schedule: any[] = [];

    for (let step = 0; step < horizonSteps; step++) {
      const hour = (step * 0.25) % 24;
      const isPeak = hour >= 17 && hour < 21;
      const isSolarMidday = hour >= 10 && hour <= 14;

      const charge = isSolarMidday ? 15.0 : 0.0;
      const discharge = isPeak ? 15.0 : 0.0;
      const cooling = hour >= 9 && hour <= 19 ? (isPeak ? 8.0 : 14.0) : 0.0;

      schedule.push({
        step,
        time_hours: step * 0.25,
        hour_of_day: hour,
        hvac_cooling_thermal_kw: cooling,
        battery_charge_kw: charge,
        battery_discharge_kw: discharge,
        predicted_grid_kw: Number((12.0 + cooling / 3.5 + charge - discharge - (isSolarMidday ? 25.0 : 0.0)).toFixed(2)),
      });
    }

    return {
      scenario: params.scenario,
      controller: params.controller,
      risk_mode: params.risk_mode,
      carbon_weight: params.carbon_weight,
      emissions_budget_kg: params.emissions_budget_kg || null,
      horizon_steps: horizonSteps,
      summary: {
        expected_cost_usd: 10.57,
        expected_emissions_kg: params.carbon_weight > 0.05 ? 18.82 : 19.50,
        battery_throughput_kwh: 128.0,
        comfort_risk_deg_hours: 0.0,
      },
      schedule,
    };
  }

  public applyManualOverride(input: DispatchOverrideInput): any {
    // 1. Idempotency Check
    const existing = this.db.prepare(`
      SELECT * FROM manual_overrides
      WHERE idempotency_key = ?
    `).get(input.idempotency_key) as any;

    if (existing) {
      return {
        override_id: existing.id,
        idempotent_replay: true,
        status: existing.status,
        message: "Duplicate request detected; returned previously processed override state.",
        override: existing,
      };
    }

    // 2. Safety Validation Layer
    // Check mutual exclusion
    let chargeKw = input.battery_charge_kw;
    let dischargeKw = input.battery_discharge_kw;
    if (chargeKw > 0 && dischargeKw > 0) {
      if (chargeKw >= dischargeKw) {
        chargeKw = chargeKw - dischargeKw;
        dischargeKw = 0;
      } else {
        dischargeKw = dischargeKw - chargeKw;
        chargeKw = 0;
      }
    }

    // Physical caps
    const clampedCooling = Math.max(0, Math.min(30.0, input.hvac_cooling_thermal_kw));
    chargeKw = Math.max(0, Math.min(25.0, chargeKw));
    dischargeKw = Math.max(0, Math.min(25.0, dischargeKw));

    const overrideId = `ovr-${crypto.randomUUID()}`;
    const auditId = `audit-${crypto.randomUUID()}`;

    // 3. Atomic Transaction: Store manual override and append-only audit event
    this.db.exec("BEGIN TRANSACTION;");
    try {
      this.db.prepare(`
        INSERT INTO manual_overrides (
          id, idempotency_key, actor, hvac_cooling_thermal_kw,
          battery_charge_kw, battery_discharge_kw, reason, duration_minutes, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
      `).run(
        overrideId,
        input.idempotency_key,
        input.actor,
        clampedCooling,
        chargeKw,
        dischargeKw,
        input.reason,
        input.duration_minutes
      );

      const beforeState = JSON.stringify({
        mode: "AUTONOMOUS_MPC",
        hvac_cooling_thermal_kw: 12.5,
        battery_charge_kw: 0.0,
        battery_discharge_kw: 15.0,
      });

      const afterState = JSON.stringify({
        mode: "MANUAL_SIMULATED_OVERRIDE",
        override_id: overrideId,
        hvac_cooling_thermal_kw: clampedCooling,
        battery_charge_kw: chargeKw,
        battery_discharge_kw: dischargeKw,
        duration_minutes: input.duration_minutes,
      });

      this.db.prepare(`
        INSERT INTO audit_events (
          id, actor, action, reason, before_state, after_state
        ) VALUES (?, ?, 'SIMULATED_MANUAL_DISPATCH_OVERRIDE', ?, ?, ?)
      `).run(auditId, input.actor, input.reason, beforeState, afterState);

      this.db.exec("COMMIT;");
    } catch (err) {
      this.db.exec("ROLLBACK;");
      throw err;
    }

    return {
      override_id: overrideId,
      idempotent_replay: false,
      status: "ACTIVE",
      simulated_notice: "Simulated override active in simulation environment only. No physical equipment is altered.",
      action_applied: {
        hvac_cooling_thermal_kw: clampedCooling,
        battery_charge_kw: chargeKw,
        battery_discharge_kw: dischargeKw,
      },
      duration_minutes: input.duration_minutes,
      audit_event_id: auditId,
    };
  }
}
