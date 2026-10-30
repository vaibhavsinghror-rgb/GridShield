"""Uncertainty and Forecast Error Stress Testing Pipeline.
Evaluates controllers against synthetic forecast errors:
- Relative Gaussian noise levels: [0.0, 0.10, 0.25, 0.40]
- Systematic forecast bias ratios: [-0.20, 0.0, +0.20]
Compares Nominal MPC vs Robust CVaR MPC.
"""

import os
import sys
import json
import argparse
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grid_sim.microgrid import MicrogridSimulator
from optimization.mpc_controller import UCCMPCController
from tests.optimization.test_ucc_mpc import extract_forecasts


def run_stress_test(output_dir: str = "experiments/results/stress_test") -> pd.DataFrame:
    os.makedirs(output_dir, exist_ok=True)
    records = []

    noise_levels = [0.0, 0.15, 0.30]
    bias_levels = [-0.15, 0.0, 0.15]
    controllers = ["nominal", "cvar"]

    rng = np.random.default_rng(42)

    for ctrl_mode in controllers:
        for noise in noise_levels:
            for bias in bias_levels:
                sim = MicrogridSimulator(scenario="typical_weekday", seed=42)
                ctrl = UCCMPCController(
                    sim.building_params, sim.hvac_params, sim.battery_params, sim.grid_limits,
                    risk_mode=ctrl_mode,
                )
                obs = sim.reset(initial_temp_c=22.5, initial_soc=0.50)

                for step in range(96):
                    fc = extract_forecasts(sim, 96)
                    # Inject noisy, biased forecast
                    err = rng.normal(0, noise, len(fc["base_demand_kw"]))
                    fc["base_demand_kw"] = np.maximum(
                        1.0, fc["base_demand_kw"] * (1.0 + bias + err)
                    )

                    action = ctrl.select_action(obs, fc)
                    sim.step(action)
                    obs = sim.get_current_observation()

                records.append({
                    "controller_mode": ctrl_mode,
                    "noise_std": noise,
                    "bias_ratio": bias,
                    "electricity_cost_usd": round(sum(t.electricity_cost for t in sim.history), 2),
                    "operational_emissions_kg": round(sum(t.operational_emissions_kg for t in sim.history), 2),
                    "comfort_violation_deg_hours": round(sum(t.comfort_violation_deg * 0.25 for t in sim.history), 3),
                    "peak_grid_kw": round(max(t.grid_power_kw for t in sim.history), 2),
                })

    df = pd.DataFrame(records)
    csv_path = os.path.join(output_dir, "stress_test_results.csv")
    df.to_csv(csv_path, index=False)
    print(f"Stress test completed and saved to {csv_path}")
    return df


if __name__ == "__main__":
    df = run_stress_test()
    print(df.to_string())
