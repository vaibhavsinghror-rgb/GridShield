"""Comprehensive Research Benchmark Pipeline.
Executes all controllers (Rule-based, Myopic, Perfect Oracle, UCC-MPC)
across identical operating scenarios and seeds.
Generates machine-readable CSV, JSON reports, and trade-off tables.
"""

import os
import sys
import time
import json
import argparse
import yaml
from typing import List, Dict, Any
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grid_sim.microgrid import MicrogridSimulator
from grid_sim.schemas import MicrogridAction
from agents.rule_based import RuleBasedController
from optimization.myopic_controller import MyopicController
from optimization.oracle_controller import PerfectInformationOracle
from optimization.mpc_controller import UCCMPCController
from tests.optimization.test_ucc_mpc import extract_forecasts


def run_benchmark_for_scenario(
    scenario: str = "typical_weekday",
    seed: int = 42,
    horizon_steps: int = 96,
) -> List[Dict[str, Any]]:
    results = []

    # Controllers to evaluate
    controller_names = ["rule_based", "myopic", "ucc_mpc", "oracle"]

    for name in controller_names:
        sim = MicrogridSimulator(scenario=scenario, seed=seed)
        obs = sim.reset(initial_temp_c=22.5, initial_soc=0.50)

        # Initialize controller
        if name == "rule_based":
            controller = RuleBasedController()
        elif name == "myopic":
            controller = MyopicController(
                sim.building_params, sim.hvac_params, sim.battery_params, sim.grid_limits
            )
        elif name == "ucc_mpc":
            controller = UCCMPCController(
                sim.building_params, sim.hvac_params, sim.battery_params, sim.grid_limits,
                risk_mode="cvar"
            )
        elif name == "oracle":
            controller = PerfectInformationOracle(
                sim.building_params, sim.hvac_params, sim.battery_params, sim.grid_limits
            )
            # Oracle pre-extracts exact realized trajectory
            sim_ref = MicrogridSimulator(scenario=scenario, seed=seed)
            sim_ref.reset(initial_temp_c=22.5, initial_soc=0.50)
            traj = {
                "outdoor_temp_c": [], "solar_irradiance_kw_m2": [], "solar_generation_kw": [],
                "base_demand_kw": [], "occupancy": [], "electricity_price": [], "carbon_intensity": []
            }
            for _ in range(horizon_steps):
                o = sim_ref.get_current_observation()
                for k in traj:
                    traj[k].append(o[k])
                sim_ref.step(MicrogridAction())
            for k in traj:
                traj[k] = np.array(traj[k])
            controller.solve_episode(traj, initial_temp_c=22.5, initial_soc=0.50)

        t0 = time.perf_counter()
        solver_failures = 0

        for step in range(horizon_steps):
            if name == "rule_based":
                action = controller.select_action(obs)
            elif name == "myopic":
                action = controller.select_action(obs)
            elif name == "ucc_mpc":
                fc = extract_forecasts(sim, horizon_steps=horizon_steps)
                action = controller.select_action(obs, fc)
                if "FAILED" in controller.last_decision_explanation.get("solver_status", ""):
                    solver_failures += 1
            elif name == "oracle":
                action = controller.get_action_for_step(step)

            sim.step(action)
            obs = sim.get_current_observation()

        solve_time = time.perf_counter() - t0

        # Compute summary metrics
        history = sim.history
        total_cost = sum(t.electricity_cost for t in history)
        total_emissions = sum(t.operational_emissions_kg for t in history)
        total_import_kwh = sum(max(0.0, t.grid_power_kw) * sim.dt_hours for t in history)
        peak_grid_kw = max(t.grid_power_kw for t in history)
        comfort_viol_deg_h = sum(t.comfort_violation_deg * sim.dt_hours for t in history)
        time_outside_comfort_pct = (sum(1 for t in history if t.comfort_violation_deg > 0.05) / horizon_steps) * 100.0
        battery_throughput = sum((t.battery_charge_kw + t.battery_discharge_kw) * sim.dt_hours for t in history)
        degrad_cost = sum(t.battery_degradation_cost for t in history)

        results.append({
            "scenario": scenario,
            "seed": seed,
            "controller": name,
            "electricity_cost_usd": round(total_cost, 2),
            "operational_emissions_kg": round(total_emissions, 2),
            "grid_import_kwh": round(total_import_kwh, 2),
            "peak_grid_kw": round(peak_grid_kw, 2),
            "comfort_violation_deg_hours": round(comfort_viol_deg_h, 3),
            "time_outside_comfort_pct": round(time_outside_comfort_pct, 1),
            "battery_throughput_kwh": round(battery_throughput, 2),
            "degradation_cost_usd": round(degrad_cost, 3),
            "solve_time_sec": round(solve_time, 3),
            "solver_failures": solver_failures,
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Run GridShield Benchmark Experiments")
    parser.add_argument("--config", type=str, default="configs/experiments/baseline.yaml")
    parser.add_argument("--out-dir", type=str, default="experiments/results/baseline")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    scenarios = [
        "typical_weekday",
        "weekend",
        "hot_summer_day",
        "solar_surplus",
        "high_carbon_evening",
    ]
    seeds = [42, 101]

    all_rows = []
    print(f"Starting GridShield Benchmark across {len(scenarios)} scenarios and {len(seeds)} seeds...")

    for scen in scenarios:
        for s in seeds:
            print(f"  Evaluating scenario '{scen}' (seed={s})...")
            rows = run_benchmark_for_scenario(scenario=scen, seed=s)
            all_rows.extend(rows)

    df = pd.DataFrame(all_rows)

    csv_path = os.path.join(args.out_dir, "benchmark_summary.csv")
    df.to_csv(csv_path, index=False)

    json_path = os.path.join(args.out_dir, "benchmark_summary.json")
    with open(json_path, "w") as f:
        json.dump(all_rows, f, indent=2)

    # Compute aggregate table grouped by controller
    agg_df = df.groupby("controller")[
        ["electricity_cost_usd", "operational_emissions_kg", "comfort_violation_deg_hours", "peak_grid_kw", "solve_time_sec"]
    ].agg(["mean", "std"])

    print("\n" + "=" * 95)
    print("GRIDSHIELD COMPREHENSIVE BENCHMARK RESULTS (Aggregated Across Scenarios)")
    print("=" * 95)
    print(agg_df.to_string())
    print("=" * 95)
    print(f"Benchmark results successfully saved to:\n  {csv_path}\n  {json_path}")


if __name__ == "__main__":
    main()
