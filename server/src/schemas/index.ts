import { z } from "zod";

export const DispatchPlanRequestSchema = z.object({
  scenario: z.string().default("typical_weekday"),
  controller: z.enum(["ucc_mpc", "rule_based", "myopic", "oracle"]).default("ucc_mpc"),
  risk_mode: z.enum(["nominal", "cvar", "worst_case"]).default("cvar"),
  carbon_weight: z.number().min(0.0).max(1.0).default(0.05),
  emissions_budget_kg: z.number().positive().optional(),
});

export const DispatchOverrideRequestSchema = z.object({
  idempotency_key: z.string().min(1, "Idempotency key is required"),
  actor: z.string().min(1, "Actor identity is required"),
  hvac_cooling_thermal_kw: z.number().min(0.0).max(30.0),
  battery_charge_kw: z.number().min(0.0).max(25.0),
  battery_discharge_kw: z.number().min(0.0).max(25.0),
  reason: z.string().min(3, "Detailed justification is required"),
  duration_minutes: z.number().int().min(15).max(480).default(60),
});

export const PaginationQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(500).default(100),
  offset: z.coerce.number().int().min(0).default(0),
});
