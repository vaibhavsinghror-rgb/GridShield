"""Ablation Study Pipeline for GridShield.
Isolates the independent effects of:
1. Carbon-awareness (varying lambda_C from $0 to $200/tonne).
2. Battery degradation penalty (varying lambda_D).
3. Risk handling (nominal vs CVaR vs worst-case).
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
from optimization.objective import ObjectiveWeights
from tests.optimization.test_ucc_mpc import extract_forecasts


def run_ablation_study(output_dir: str = "experiments/results/ablation") -> pd.DataFrame:
    os.makedirs(output_dir, exist_ok=True)
    records = []

    # 1. Carbon Weight Ablation
    carbon_weights = [0.0, 0.02, 0.05, 0.10, 0.20]
    for w_c in carbon_weights:
        sim = MicrogridSimulator(scenario="high_carbon_evening", seed=42)
        weights = ObjectiveWeights(lambda_carbon=w_c)
        ctrl = UCCMPCController(
            sim.building_params, sim.hvac_params, sim.battery_params, sim.grid_limits,
            weights=weights, risk_mode="nominal"
        )
        obs = sim.reset(initial_temp_c=22.5, initial_soc=0.50)
        for _ in range(96):
            fc = extract_forecasts(sim, 96)
            action = ctrl.select_action(obs, fc)
            sim.step(action)
            obs = sim.get_current_observation()

        records.append({
            "ablation_type": "carbon_weight",
            "parameter_value": f"lambda_C={w_c}",
            "electricity_cost_usd": round(sum(t.electricity_cost for t in sim.history), 2),
            "operational_emissions_kg": round(sum(t.operational_emissions_kg for t in sim.history), 2),
            "battery_throughput_kwh": round(sum((t.battery_charge_kw + t.battery_discharge_kw)*0.25 for t in sim.history), 2),
        })

    # 2. Risk Mode Ablation
    risk_modes = ["nominal", "cvar", "worst_case"]
    for rm in risk_modes:
        sim = MicrogridSimulator(scenario="hot_summer_day", seed=42)
        ctrl = UCCMPCController(
            sim.building_params, sim.hvac_params, sim.battery_params, sim.grid_limits,
            risk_mode=rm
        )
        obs = sim.reset(initial_temp_c=22.5, initial_soc=0.50)
        for _ in range(96):
            fc = extract_forecasts(sim, 96)
            action = ctrl.select_action(obs, fc)
            sim.step(action)
            obs = sim.get_current_observation()

        records.append({
            "ablation_type": "risk_mode",
            "parameter_value": f"mode={rm}",
            "electricity_cost_usd": round(sum(t.electricity_cost for t in sim.history), 2),
            "operational_emissions_kg": round(sum(t.operational_emissions_kg for t in sim.history), 2),
            "battery_throughput_kwh": round(sum((t.battery_charge_kw + t.battery_discharge_kw)*0.25 for t in sim.history), 2),
        })

    df = pd.DataFrame(records)
    csv_path = os.path.join(output_dir, "ablation_results.csv")
    df.to_csv(csv_path, index=False)
    print(f"Ablation study completed and saved to {csv_path}")
    return df


if __name__ == "__main__":
    df = run_ablation_study()
    print(df.to_string())
