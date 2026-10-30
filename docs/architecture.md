# GridShield Architecture Documentation

## 1. System Overview

GridShield is a simulation-first energy management and decision-support platform designed for commercial buildings and microgrids. It coordinates building HVAC energy consumption, battery energy storage systems (BESS), solar PV generation, and utility grid inter-ties subject to time-of-use (TOU) tariffs and real-time grid carbon-intensity signals.

```
                      +---------------------------------------+
                      |       React + Vite Dashboard          |
                      |  (KPIs, 7 Charts, Dispatch Planner)   |
                      +-------------------+-------------------+
                                          | REST / JSON
                                          v
                      +---------------------------------------+
                      |         Node.js + Express API         |
                      |    (SQLite, Zod, Idempotent Overrides)|
                      +-------------------+-------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                                                   |
        v                                                                   v
+-----------------------+                                         +-----------------------+
|  PyTorch Transformer  |                                         | SciPy HiGHS Optimizer |
|  Forecasting Engine   |                                         |  (UCC-MPC, Myopic,    |
| (Residual Uncertainty)|                                         |   Oracle Benchmark)   |
+-----------+-----------+                                         +-----------+-----------+
            | Forecast Trajectories                                           | Actions
            +---------------------------------+-------------------------------+
                                              |
                                              v
                                  +-----------------------+
                                  | Action Safety Filter  |
                                  | (Hard Invariant Guard)|
                                  +-----------+-----------+
                                              | Verified Actions
                                              v
                                  +-----------------------+
                                  | Microgrid Simulator   |
                                  | (Building RC, BESS,   |
                                  |  Solar PV, Tariffs)   |
                                  +-----------------------+
```

## 2. Component Design

### 2.1 Physics Simulator (`grid_sim/`)
- **Building Thermal Zone**: Single-zone continuous/discrete Resistance-Capacitance (RC) thermodynamic model with explicit envelope heat transfer, occupancy gains, and solar aperture radiation.
- **HVAC Subsystem**: Electrically-coupled thermal heat pump / central chiller with distinct cooling and heating capacities governed by physical Coefficient of Performance (COP).
- **Battery Energy Storage System (BESS)**: Discrete state-of-charge tracking with independent charge and discharge efficiencies, power limits, and throughput-based degradation proxy.
- **Power Balance & Grid Inter-tie**: Enforces strict physical Kirchhoff power balance ($P_{\mathrm{grid}} = P_{\mathrm{base}} + P_{\mathrm{HVAC}} + P_c - P_d - P_{\mathrm{solar}}$) and caps import and export limits.

### 2.2 Forecasting Subsystem (`forecasting/`)
- Multi-head self-attention PyTorch Temporal Transformer for rolling 24-hour ahead horizon prediction.
- Benchmarked against Persistence, Seasonal-Naive, and Ridge Regression models.
- Chronologically partitioned (70% train, 15% validation, 15% test) without forward data leakage.
- Generates empirical residual dispersion prediction intervals (10%, 50%, 90%).

### 2.3 Optimization Subsystem (`optimization/`)
- **UCC-MPC**: Uncertainty-Aware Carbon-Constrained Model Predictive Control. Solves rolling horizon multi-period Linear Programs using SciPy's HiGHS solver.
- **Conditional Value-at-Risk (CVaR)**: Risk-sensitive scenario evaluation mitigating forecast uncertainty spikes.
- **Action Safety Filter**: Immutable physical barrier clamping requested setpoints against hard bounds (no simultaneous charge/discharge, thermal capacity caps, SoC limits).

### 2.4 Backend REST API (`server/`)
- Express 4.x with native `node:sqlite` transaction engine.
- Zod schema validation across all inputs.
- Idempotency key tracking on manual dispatch overrides.
- Append-only audit logs recording actor, timestamp, action, reason, and before/after states.

### 2.5 Frontend Dashboard (`src/`)
- High-performance responsive React single-page application built with Vite and Tailwind CSS.
- 7 comprehensive Recharts visualizations.
- Interactive Dispatch Planner with sensitivity sliders and simulated override modal.
