"""CLI script to run a 24-hour microgrid simulation with a selected controller.
Usage:
    python scripts/run_simulation.py --scenario typical_weekday --controller ucc_mpc
"""

import os
import sys
import argparse
import yaml
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grid_sim.microgrid import MicrogridSimulator
from agents.rule_based import RuleBasedController
from optimization.myopic_controller import MyopicController
from optimization.mpc_controller import UCCMPCController
from tests.optimization.test_ucc_mpc import extract_forecasts


def main():
    parser = argparse.ArgumentParser(description="Run GridShield Microgrid Simulation")
    parser.add_argument("--config", type=str, default="configs/sim_grid.yaml", help="Path to config")
    parser.add_argument("--scenario", type=str, default="typical_weekday", help="Operating scenario")
    parser.add_argument("--controller", type=str, default="ucc_mpc", choices=["rule_based", "myopic", "ucc_mpc"])
    parser.add_argument("--seed", type=int, default=42, help="Seed")
    args = parser.parse_args()

    print(f"Initializing GridShield Simulator [scenario={args.scenario}, controller={args.controller}]...")
    sim = MicrogridSimulator(scenario=args.scenario, seed=args.seed)

    if args.controller == "rule_based":
        ctrl = RuleBasedController()
    elif args.controller == "myopic":
        ctrl = MyopicController(sim.building_params, sim.hvac_params, sim.battery_params, sim.grid_limits)
    else:
        ctrl = UCCMPCController(sim.building_params, sim.hvac_params, sim.battery_params, sim.grid_limits)

    obs = sim.reset(initial_temp_c=22.5, initial_soc=0.50)

    for step in range(96):
        if args.controller == "ucc_mpc":
            fc = extract_forecasts(sim, 96)
            action = ctrl.select_action(obs, fc)
        else:
            action = ctrl.select_action(obs)
        sim.step(action)
        obs = sim.get_current_observation()

    # Telemetry report
    total_cost = sum(t.electricity_cost for t in sim.history)
    total_emissions = sum(t.operational_emissions_kg for t in sim.history)
    peak_grid = max(t.grid_power_kw for t in sim.history)
    comfort_viols = sum(t.comfort_violation_deg * 0.25 for t in sim.history)
    battery_throughput = sum((t.battery_charge_kw + t.battery_discharge_kw) * 0.25 for t in sim.history)

    print("\n" + "=" * 50)
    print("SIMULATION RUN REPORT (24 Hours / 96 Steps)")
    print("=" * 50)
    print(f"Total Electricity Cost:     ${total_cost:.2f}")
    print(f"Total Operational Emissions: {total_emissions:.2f} kgCO2")
    print(f"Peak Grid Import:            {peak_grid:.2f} kW")
    print(f"Comfort Violations:          {comfort_viols:.3f} °C-hours")
    print(f"Battery Energy Throughput:   {battery_throughput:.2f} kWh")
    print("=" * 50)


if __name__ == "__main__":
    main()
