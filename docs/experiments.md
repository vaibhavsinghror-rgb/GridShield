# GridShield Experimental Results and Benchmark Report

## 1. Experimental Methodology

All controllers were evaluated under identical exogenous scenario seeds and initial conditions ($T_0 = 22.5^\circ\text{C}, \text{SoC}_0 = 0.50$):
- **Typical Weekday**: Standard occupancy (40 occupants 08:00-17:00), ambient temperature peaking at 30°C.
- **Weekend**: Low building occupancy, light base electrical demand.
- **Hot Summer Day**: Extreme heatwave peaking at 40°C, elevated cooling requirement.
- **Solar Surplus**: High solar irradiance ($1.0\text{ kW/m}^2$) with surplus midday renewable generation.
- **High-Carbon Evening Peak**: Peaking thermal generation driving grid carbon intensity to $450\text{ gCO}_2/\text{kWh}$ from 17:00 to 21:00.

## 2. Benchmark Summary Results

Aggregated across all scenarios and seeds ($N=96$ steps per episode):

| Controller | Mean Cost ($) | Mean Emissions (kg) | Comfort Violations (°C-h) | Peak Grid Import (kW) | Mean Solve Time (s) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UCC-MPC (Proposed)** | **$10.57** ($\pm 7.72$) | **19.50 kg** ($\pm 15.98$) | **0.000** ($\pm 0.001$) | 30.76 kW ($\pm 12.15$) | 1.52 s |
| **Perfect Oracle (Lower Bound)** | $10.48 ($\pm 7.73$) | 19.22 kg ($\pm 16.14$) | 0.000 ($\pm 0.001$) | 30.31 kW ($\pm 11.98$) | 0.001 s |
| **Rule-Based Heuristic** | $17.52 ($\pm 6.09$) | 40.14 kg ($\pm 9.30$) | 4.332 ($\pm 8.42$) | 25.71 kW ($\pm 2.03$) | 0.001 s |
| **Myopic 1-Step LP** | $20.03 ($\pm 5.75$) | 33.89 kg ($\pm 11.23$) | 42.111 ($\pm 39.29$) | 17.05 kW ($\pm 0.25$) | 0.091 s |

### Key Research Findings
1. **Cost & Carbon Reduction**: UCC-MPC achieves a **39.7% cost reduction** and a **51.4% emissions reduction** relative to the Rule-Based heuristic baseline.
2. **Optimality Gap**: UCC-MPC operates within **0.8% of the theoretical lower bound** established by the non-causal Perfect Information Oracle.
3. **Failure Mode of Myopic Optimization**: Without multi-step horizon lookahead, the single-step myopic optimizer delays cooling until temperatures breach comfort limits, causing severe thermal cycling and massive comfort penalties (42.1 °C-hours).

## 3. Carbon-Awareness Ablation Study

Sensitivity to the carbon penalty weight $\lambda_C$ in high-carbon evening peaking scenarios:

| Carbon Weight ($\lambda_C$) | Electricity Cost ($) | Operational Emissions (kg) | BESS Throughput (kWh) |
| :--- | :--- | :--- | :--- |
| $\lambda_C = \$0/\text{tonne}$ | $10.82 | 20.76 kg | 128.1 kWh |
| $\lambda_C = \$20/\text{tonne}$ | $10.81 | 20.19 kg | 129.0 kWh |
| $\lambda_C = \$50/\text{tonne}$ | $10.82 | 19.35 kg | 130.2 kWh |
| $\lambda_C = \$100/\text{tonne}$ | $10.85 | 18.82 kg | 131.5 kWh |
| $\lambda_C = \$200/\text{tonne}$ | $10.94 | 18.16 kg | 132.2 kWh |

**Insight**: Increasing $\lambda_C$ from $0 to $200/tonne achieves a **12.5% reduction in grid carbon emissions** for only a **1.1% increase in monetary electricity expenditure**.

## 4. Forecasting Model Benchmark

Evaluated across the 15% out-of-sample chronological test set:

| Model | MAE (kW) | RMSE (kW) | Normalized RMSE (NRMSE) |
| :--- | :--- | :--- | :--- |
| **Ridge Regression** | **2.3873** | **2.9273** | **0.1951** |
| **Temporal Transformer** | 4.2874 | 5.3435 | 0.3562 |
| **Seasonal Naive** | 6.7083 | 9.5876 | 0.6390 |
| **Persistence** | 6.9553 | 9.8997 | 0.6598 |
