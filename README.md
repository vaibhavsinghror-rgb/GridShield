# GridShield: Autonomous, Carbon-Aware Micro-Grid Energy Management Platform

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-v24-green.svg)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-Strict-blue.svg)](https://www.typescriptlang.org/)
[![Tests](https://img.shields.io/badge/Tests-22%20Python%20%7C%208%20Jest%20Passing-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

GridShield is a simulation-first energy management and decision-support platform designed for commercial buildings and microgrids. It coordinates flexible HVAC consumption, battery energy storage systems (BESS), solar PV generation, and utility grid inter-ties to minimize electricity expenditure and operational grid carbon emissions while guaranteeing thermal comfort and battery safety.

> **Disclaimer**: GridShield is a simulation-first research and decision-support platform. It is not certified for direct supervisory control of live physical electrical infrastructure or utility switchgear.

---

## 1. Central Research Question & Contribution

> *Can uncertainty-aware, carbon-aware predictive dispatch outperform conventional energy-management baselines across diverse operating scenarios without compromising comfort or battery constraints?*

GridShield implements **UCC-MPC (Uncertainty-Aware Carbon-Constrained Model Predictive Control)**:
1. **Rolling-Horizon Lookahead**: 24-hour horizon ($H=96$ steps of 15 minutes) linear optimization solved via SciPy's HiGHS solver.
2. **Joint Economic & Carbon Optimization**: Simultaneously minimizes electricity tariffs and grid marginal emissions ($\mathrm{gCO}_2/\mathrm{kWh}$).
3. **Uncertainty & Risk-Sensitivity**: Incorporates empirical Conditional Value-at-Risk ($\mathrm{CVaR}_\alpha$) across forecast scenarios to safeguard against tail-risk demand surges.
4. **Action Safety Filter**: An immutable physical runtime governor verifying all control setpoints against thermal capacities, BESS SoC bounds, and mutual exclusion rules.

---

## 2. Benchmark Evaluation Summary

Evaluated across 5 diverse operational scenarios (**Typical Weekday**, **Weekend**, **Hot Summer Day Heatwave**, **Solar Surplus**, and **High-Carbon Peaking Evening**) under identical initial conditions ($T_0 = 22.5^\circ\mathrm{C}, \mathrm{SoC}_0 = 0.50$):

| Controller | Mean Cost ($) | Mean Emissions (kg) | Comfort Violations (°C-h) | Peak Grid Import (kW) | Solve Time (s) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UCC-MPC (Ours)** | **$10.57** ($\pm 7.72$) | **19.50 kg** ($\pm 15.98$) | **0.000** ($\pm 0.001$) | 30.76 kW ($\pm 12.15$) | 1.52 s |
| **Oracle (Lower Bound)** | $10.48 ($\pm 7.73$) | 19.22 kg ($\pm 16.14$) | 0.000 ($\pm 0.001$) | 30.31 kW ($\pm 11.98$) | 0.001 s |
| **Rule-Based Baseline** | $17.52 ($\pm 6.09$) | 40.14 kg ($\pm 9.30$) | 4.332 ($\pm 8.42$) | 25.71 kW ($\pm 2.03$) | 0.001 s |
| **Myopic 1-Step LP** | $20.03 ($\pm 5.75$) | 33.89 kg ($\pm 11.23$) | 42.111 ($\pm 39.29$) | 17.05 kW ($\pm 0.25$) | 0.091 s |

**Key Results**:
- UCC-MPC achieves a **39.7% cost reduction** and a **51.4% emissions reduction** relative to the rule-based baseline.
- Operates within **0.8% of the theoretical lower bound** established by the perfect-information oracle.
- Carbon sensitivity ablation shows increasing $\lambda_C$ reduces emissions by **12.5%** with only a **1.1% increase in monetary expense**.

---

## 3. Technology Stack

- **Physics & Simulator**: Python 3.11, NumPy, SciPy (HiGHS LP solver), pandas, Pydantic v2.
- **Forecasting & ML**: PyTorch (Temporal Transformer), scikit-learn (Ridge baseline).
- **Reinforcement Learning**: Farama Gymnasium, Stable-Baselines3 (PPO).
- **Backend REST API**: Node.js v24, Express, TypeScript, native `node:sqlite` with migrations and transactions, Zod.
- **Frontend Dashboard**: React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide icons.
- **Testing**: `pytest` (22 tests), `jest` + `supertest` (8 tests).

---

## 4. Quickstart Commands

### 4.1 Python Environment & Tests
```bash
# Verify installation
python scripts/verify_installation.py

# Run all 22 Python physics, forecasting, optimization, and contract tests
pytest -v

# Run 24-hour simulation with UCC-MPC
python scripts/run_simulation.py --scenario typical_weekday --controller ucc_mpc

# Train and evaluate forecaster
python scripts/train_forecaster.py --epochs 6

# Execute full research benchmark pipeline
python experiments/run_benchmark.py
```

### 4.2 Backend REST API
```bash
cd server
npm install
npm test       # Run 8 Jest/Supertest integration tests
npm run dev    # Start API server on http://localhost:4000
```

### 4.3 Frontend Operations Dashboard
```bash
# In project root
npm install
npm run build  # Verify strict TypeScript compilation and production bundle
npm run dev    # Start Vite dashboard on http://localhost:3000
```

---

## 5. Repository Structure

```text
GridShield/
├── README.md
├── LICENSE
├── Makefile
├── pyproject.toml
├── package.json
├── docker-compose.yml
│
├── configs/                       # Simulation, MPC, and experiment configs
│   ├── parameters.yaml
│   ├── sim_grid.yaml
│   ├── forecasting.yaml
│   └── optimization.yaml
│
├── grid_sim/                      # Track A: Physically consistent simulator
│   ├── building.py                # Single-zone RC thermal model
│   ├── battery.py                 # 100 kWh BESS with throughput degradation
│   ├── hvac.py                    # COP-coupled chiller / heat pump
│   ├── solar.py                   # 40 kW PV array model
│   ├── tariffs.py                 # Time-of-use tariffs
│   ├── carbon.py                  # Real-time grid carbon intensity
│   ├── microgrid.py               # Unified power balance simulator
│   └── schemas.py                 # Pydantic v2 physical schemas
│
├── forecasting/                   # Track B: Time-series forecasting
│   ├── transformer.py             # PyTorch Temporal Transformer
│   ├── baselines.py               # Persistence, Seasonal-Naive, Ridge
│   ├── dataset.py                 # Chronological time-series dataset
│   └── predict.py                 # Calibrated uncertainty & prediction intervals
│
├── optimization/                  # Track C: Carbon-aware optimization
│   ├── mpc_controller.py          # UCC-MPC rolling-horizon LP controller
│   ├── myopic_controller.py       # 1-step local optimizer
│   ├── oracle_controller.py       # Global perfect-information benchmark
│   ├── safety_filter.py           # Invariant physical guard
│   └── uncertainty.py             # CVaR tail-risk formulation
│
├── engagement_env/                # Track D: Gymnasium environment
│   ├── energy_env.py              # Gym environment with safety filter
│   └── reward.py                  # Multi-objective reward scaling
│
├── agents/                        # Controllers & PPO Agent
│   ├── rule_based.py              # Heuristic rule-based baseline
│   └── ppo_agent.py               # Stable-Baselines3 PPO agent
│
├── experiments/                   # Track E: Research evaluation
│   ├── run_benchmark.py           # Multi-scenario multi-seed benchmark
│   ├── run_ablation.py            # Carbon and risk sensitivity ablations
│   └── results/                   # Machine-readable CSVs, JSONs, and metrics
│
├── server/                        # Track F: Node.js Express REST API
│   ├── src/
│   │   ├── app.ts                 # Express configuration
│   │   ├── db/database.ts         # Native node:sqlite migrations
│   │   ├── routes/api.ts          # REST endpoints
│   │   └── services/              # Dispatch and telemetry services
│   └── tests/api.test.ts          # Supertest integration tests
│
├── src/                           # Track G: React Operations Dashboard
│   ├── components/                # KPIs, 7 Charts, Planner, Overrides, Audit
│   └── App.tsx                    # Main operations layout
│
└── docs/                          # Comprehensive technical documentation
    ├── architecture.md
    ├── mathematical_model.md
    ├── api_reference.md
    ├── experiments.md
    ├── limitations.md
    └── literature_review.md
```

---

## 6. Safety & Verification Summary

- **Total Automated Tests**: 30 automated tests (22 Python + 8 TypeScript Jest).
- **Physics Conservation**: Verified against analytical hand-calculated thermodynamic solutions.
- **Auditing**: Append-only audit stream tracking all simulated overrides and state transitions with mandatory justification.
- **Idempotency**: Duplicate requests resolved atomically using idempotency keys.
