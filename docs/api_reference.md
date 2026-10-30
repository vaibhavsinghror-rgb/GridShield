# GridShield API Reference

The GridShield backend exposes a versioned REST API at `/api`.

## 1. System Endpoints

### `GET /api/health`
Checks operational state of the backend and simulator engine.
**Response (200 OK):**
```json
{
  "status": "HEALTHY",
  "platform": "GridShield Decision Support Platform",
  "engine": "Deterministic Simulation & UCC-MPC Optimizer",
  "version": "0.1.0",
  "timestamp": "2026-10-30T03:00:00.000Z"
}
```

### `GET /api/assets`
Returns all registered microgrid physical assets (BESS, Solar PV array, Chiller, Grid Inter-tie).

---

## 2. Telemetry Endpoints

### `GET /api/telemetry/current`
Returns the most recent 15-minute simulation telemetry frame.

### `GET /api/telemetry/history`
Query parameters:
- `limit` (optional, default: 96, max: 500)
- `offset` (optional, default: 0)

Returns chronologically ordered telemetry time series.

---

## 3. Dispatch & Planning Endpoints

### `GET /api/dispatch/current`
Returns currently active dispatch setpoints, active constraints, and decision explanation.

### `POST /api/dispatch/plan`
Generates an optimized 24-hour dispatch schedule without modifying current state.
**Request Body:**
```json
{
  "scenario": "typical_weekday",
  "controller": "ucc_mpc",
  "risk_mode": "cvar",
  "carbon_weight": 0.05,
  "emissions_budget_kg": 120.0
}
```
**Response (200 OK):**
```json
{
  "scenario": "typical_weekday",
  "controller": "ucc_mpc",
  "horizon_steps": 96,
  "summary": {
    "expected_cost_usd": 10.57,
    "expected_emissions_kg": 19.50,
    "battery_throughput_kwh": 128.0,
    "comfort_risk_deg_hours": 0.0
  },
  "schedule": [...]
}
```

### `POST /api/dispatch/override`
Applies a simulated manual control override with atomic audit event generation and idempotency guarantees.
**Request Body:**
```json
{
  "idempotency_key": "unique-uuid-key",
  "actor": "Facility-Operator-01",
  "hvac_cooling_thermal_kw": 15.0,
  "battery_charge_kw": 0.0,
  "battery_discharge_kw": 10.0,
  "reason": "Peak load curtailment event",
  "duration_minutes": 60
}
```
**Response:**
- `201 Created`: First time processed.
- `200 OK`: Duplicate request (idempotent replay).

---

## 4. Analytics & Governance Endpoints

### `GET /api/analytics/summary`
Returns unified KPIs: daily electricity expenditure, operational grid emissions, peak import, degree-hours of comfort violations, and baseline comparison.

### `GET /api/audit-logs`
Returns append-only audit stream tracking all manual overrides, reasons, and state diffs.

### `GET /api/experiments`
Returns saved benchmark experiment artifacts.
