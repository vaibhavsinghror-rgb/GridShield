import request from "supertest";
import { createApp } from "../src/app.js";
import { getDatabase } from "../src/db/database.js";
import { DatabaseSync } from "node:sqlite";

describe("GridShield Backend API Integration Test Suite", () => {
  let db: DatabaseSync;
  let app: any;

  beforeAll(() => {
    // Isolated in-memory database for testing
    db = getDatabase(":memory:");
    app = createApp(db);
  });

  it("GET /api/health returns 200 and healthy status", async () => {
    const res = await request(app).get("/api/health");
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("HEALTHY");
    expect(res.body.platform).toContain("GridShield");
  });

  it("GET /api/assets returns registered microgrid assets", async () => {
    const res = await request(app).get("/api/assets");
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBeGreaterThanOrEqual(4);
  });

  it("GET /api/telemetry/history returns 24-hour simulation telemetry", async () => {
    const res = await request(app).get("/api/telemetry/history?limit=96");
    expect(res.status).toBe(200);
    expect(res.body.data.length).toBe(96);
    expect(res.body.data[0]).toHaveProperty("indoor_temp_c");
    expect(res.body.data[0]).toHaveProperty("grid_power_kw");
  });

  it("GET /api/analytics/summary returns KPI calculations and baseline comparisons", async () => {
    const res = await request(app).get("/api/analytics/summary");
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty("today_electricity_cost_usd");
    expect(res.body).toHaveProperty("today_emissions_kg");
    expect(res.body.baseline_comparison).toHaveProperty("savings_usd");
  });

  it("POST /api/dispatch/plan returns scheduled dispatch for horizon", async () => {
    const res = await request(app)
      .post("/api/dispatch/plan")
      .send({
        scenario: "typical_weekday",
        controller: "ucc_mpc",
        risk_mode: "cvar",
        carbon_weight: 0.05,
      });

    expect(res.status).toBe(200);
    expect(res.body.schedule.length).toBe(96);
    expect(res.body.summary).toHaveProperty("expected_cost_usd");
  });

  it("POST /api/dispatch/override validates and creates atomic override and audit event", async () => {
    const idempotencyKey = `test-key-${Date.now()}`;
    const payload = {
      idempotency_key: idempotencyKey,
      actor: "Operator-01",
      hvac_cooling_thermal_kw: 20.0,
      battery_charge_kw: 10.0,
      battery_discharge_kw: 0.0,
      reason: "Emergency test override for extreme solar event",
      duration_minutes: 60,
    };

    const res = await request(app).post("/api/dispatch/override").send(payload);
    expect(res.status).toBe(201);
    expect(res.body.override_id).toBeDefined();
    expect(res.body.idempotent_replay).toBe(false);
    expect(res.body.audit_event_id).toBeDefined();

    // Verify audit log was recorded
    const auditRes = await request(app).get("/api/audit-logs");
    expect(auditRes.status).toBe(200);
    expect(auditRes.body.data.length).toBeGreaterThan(0);
    const logged = auditRes.body.data.find((e: any) => e.reason === payload.reason);
    expect(logged).toBeDefined();
    expect(logged.actor).toBe("Operator-01");
  });

  it("POST /api/dispatch/override enforces idempotency on duplicate submission", async () => {
    const idempotencyKey = `idemp-key-repeat-${Date.now()}`;
    const payload = {
      idempotency_key: idempotencyKey,
      actor: "Operator-02",
      hvac_cooling_thermal_kw: 15.0,
      battery_charge_kw: 0.0,
      battery_discharge_kw: 10.0,
      reason: "Peak load curtailment",
      duration_minutes: 30,
    };

    const first = await request(app).post("/api/dispatch/override").send(payload);
    expect(first.status).toBe(201);
    expect(first.body.idempotent_replay).toBe(false);

    // Duplicate submission
    const second = await request(app).post("/api/dispatch/override").send(payload);
    expect(second.status).toBe(200);
    expect(second.body.idempotent_replay).toBe(true);
    expect(second.body.override_id).toBe(first.body.override_id);
  });

  it("POST /api/dispatch/override rejects invalid payload with 400", async () => {
    const res = await request(app).post("/api/dispatch/override").send({
      idempotency_key: "bad-req",
      hvac_cooling_thermal_kw: -10.0, // Invalid negative cooling
    });
    expect(res.status).toBe(400);
    expect(res.body.error).toBeDefined();
  });
});
