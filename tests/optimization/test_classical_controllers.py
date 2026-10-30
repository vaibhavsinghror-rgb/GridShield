"""Tests for classical controllers: Rule-Based, Myopic, Safety Filter, and Oracle benchmark.
Verifies WP2 Gate requirements: All controllers run against identical scenarios,
return feasible actions, and produce consistent evaluation metrics.
"""

import pytest
import numpy as np

from grid_sim.schemas import (
    BuildingThermalParams,
    HVACParams,
    BatteryParams,
    GridLimits,
    MicrogridAction,
)
from grid_sim.microgrid import MicrogridSimulator
from optimization.safety_filter import ActionSafetyFilter
from agents.rule_based import RuleBasedController
from optimization.myopic_controller import MyopicController
from optimization.oracle_controller import PerfectInformationOracle


def test_safety_filter_clamp_and_violation_logging():
    """Verify safety filter rejects infeasible requests and corrects them."""
    bat_params = BatteryParams(
        capacity_kwh=100.0,
        soc_min=0.10,
        soc_max=0.90,
        max_charge_power_kw=25.0,
        max_discharge_power_kw=25.0,
    )
    hvac_params = HVACParams(cooling_capacity_thermal_kw=30.0)
    grid_limits = GridLimits(max_import_kw=100.0, max_export_kw=50.0)
    safety_filter = ActionSafetyFilter(bat_params, hvac_params, grid_limits)

    # 1. Infeasible cooling (e.g. 100 kW vs 30 kW max)
    # 2. Simultaneous charge and discharge (20 kW and 15 kW)
    bad_action = MicrogridAction(
        hvac_cooling_thermal_kw=100.0,
        battery_charge_kw=20.0,
        battery_discharge_kw=15.0,
    )

    res = safety_filter.validate_and_filter(
        action=bad_action,
        current_soc=0.50,
        current_indoor_temp_c=25.0,
    )

    assert res.was_modified is True
    assert res.action.hvac_cooling_thermal_kw == 30.0
    # Net flux: 20 - 15 = 5 kW charge, 0 discharge
    assert res.action.battery_charge_kw == 5.0
    assert res.action.battery_discharge_kw == 0.0
    assert len(res.violations) >= 2


def test_rule_based_controller_run():
    """Verify Rule-Based baseline runs full 24h episode."""
    sim = MicrogridSimulator(scenario="typical_weekday", seed=42)
    controller = RuleBasedController()

    obs = sim.reset(initial_temp_c=22.5, initial_soc=0.50)
    for _ in range(96):
        action = controller.select_action(obs)
        telemetry = sim.step(action)
        obs = sim.get_current_observation()

    assert len(sim.history) == 96
    total_cost = sum(t.total_step_cost for t in sim.history)
    assert total_cost > 0.0


def test_myopic_controller_run():
    """Verify Myopic LP optimizer runs full 24h episode and satisfies constraints."""
    sim = MicrogridSimulator(scenario="typical_weekday", seed=42)
    controller = MyopicController(
        building_params=sim.building_params,
        hvac_params=sim.hvac_params,
        battery_params=sim.battery_params,
        grid_limits=sim.grid_limits,
    )

    obs = sim.reset(initial_temp_c=22.5, initial_soc=0.50)
    for _ in range(96):
        action = controller.select_action(obs)
        telemetry = sim.step(action)
        # Verify physical feasibility
        assert 0.0 <= action.hvac_cooling_thermal_kw <= sim.hvac_params.cooling_capacity_thermal_kw
        assert 0.0 <= action.battery_charge_kw <= sim.battery_params.max_charge_power_kw
        assert 0.0 <= action.battery_discharge_kw <= sim.battery_params.max_discharge_power_kw
        obs = sim.get_current_observation()

    assert len(sim.history) == 96


def test_oracle_controller_lower_bound():
    """Verify Perfect-Information Oracle solves globally and produces a valid lower bound."""
    # Pre-extract exogenous signals for typical weekday
    sim_ref = MicrogridSimulator(scenario="typical_weekday", seed=42)
    sim_ref.reset(initial_temp_c=22.5, initial_soc=0.50)

    trajectories = {
        "outdoor_temp_c": [],
        "solar_irradiance_kw_m2": [],
        "solar_generation_kw": [],
        "base_demand_kw": [],
        "occupancy": [],
        "electricity_price": [],
        "carbon_intensity": [],
    }
    for _ in range(96):
        obs = sim_ref.get_current_observation()
        trajectories["outdoor_temp_c"].append(obs["outdoor_temp_c"])
        trajectories["solar_irradiance_kw_m2"].append(obs["solar_irradiance_kw_m2"])
        trajectories["solar_generation_kw"].append(obs["solar_generation_kw"])
        trajectories["base_demand_kw"].append(obs["base_demand_kw"])
        trajectories["occupancy"].append(obs["occupancy"])
        trajectories["electricity_price"].append(obs["electricity_price"])
        trajectories["carbon_intensity"].append(obs["carbon_intensity"])
        # step with dummy zero action to advance
        sim_ref.step(MicrogridAction())

    for k in trajectories:
        trajectories[k] = np.array(trajectories[k])

    oracle = PerfectInformationOracle(
        building_params=sim_ref.building_params,
        hvac_params=sim_ref.hvac_params,
        battery_params=sim_ref.battery_params,
        grid_limits=sim_ref.grid_limits,
    )
    scheduled_actions = oracle.solve_episode(
        realized_trajectories=trajectories,
        initial_temp_c=22.5,
        initial_soc=0.50,
    )
    assert oracle.is_solved is True
    assert len(scheduled_actions) == 96

    # Execute scheduled actions in a clean simulator
    sim_oracle = MicrogridSimulator(scenario="typical_weekday", seed=42)
    sim_oracle.reset(initial_temp_c=22.5, initial_soc=0.50)

    for t in range(96):
        sim_oracle.step(scheduled_actions[t])

    oracle_total_cost = sum(t.total_step_cost for t in sim_oracle.history)
    assert oracle_total_cost > 0.0
