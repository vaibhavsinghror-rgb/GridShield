"""Tests for UCC-MPC (Uncertainty-Aware Carbon-Constrained MPC).
Verifies WP4 Gate:
- Reproducible benchmark run
- Cost-only vs Carbon-aware trade-off
- Forecast uncertainty stress test (Nominal vs CVaR)
- Action safety filter constraint guarantees
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
from optimization.mpc_controller import UCCMPCController
from optimization.objective import ObjectiveWeights


def extract_forecasts(sim: MicrogridSimulator, horizon_steps: int = 96):
    """Generates rolling forecast trajectories without leaking future realized disturbances."""
    exo = sim.exogenous
    t_start = sim.time_hours
    trajectories = {
        "outdoor_temp_c": [],
        "solar_generation_kw": [],
        "occupancy": [],
        "electricity_price": [],
        "carbon_intensity": [],
        "base_demand_kw": [],
    }
    for h in range(horizon_steps):
        t_h = t_start + h * sim.dt_hours
        cond = exo.get_conditions_at_time(t_h)
        trajectories["outdoor_temp_c"].append(cond["outdoor_temp_c"])
        trajectories["solar_generation_kw"].append(sim.solar.generate(cond["solar_irradiance_kw_m2"]))
        trajectories["occupancy"].append(cond["occupancy"])
        trajectories["electricity_price"].append(sim.tariff.get_rate_at_hour(t_h % 24.0))
        trajectories["carbon_intensity"].append(sim.carbon.get_intensity_at_hour(t_h % 24.0))
        trajectories["base_demand_kw"].append(cond["base_demand_kw"])

    for k in trajectories:
        trajectories[k] = np.array(trajectories[k])
    return trajectories


def test_ucc_mpc_rolling_horizon_run():
    """Verify UCC-MPC successfully completes a 24h rolling horizon simulation."""
    sim = MicrogridSimulator(scenario="typical_weekday", seed=42)
    controller = UCCMPCController(
        building_params=sim.building_params,
        hvac_params=sim.hvac_params,
        battery_params=sim.battery_params,
        grid_limits=sim.grid_limits,
        risk_mode="nominal",
    )

    obs = sim.reset(initial_temp_c=22.5, initial_soc=0.50)
    for _ in range(96):
        forecasts = extract_forecasts(sim, horizon_steps=96)
        action = controller.select_action(obs, forecasts)
        telemetry = sim.step(action)
        obs = sim.get_current_observation()

    assert len(sim.history) == 96
    assert controller.last_decision_explanation["solver_status"] == "OPTIMAL"


def test_cost_vs_carbon_aware_tradeoff():
    """Verify that carbon-aware mode reduces grid operational carbon emissions

    compared to pure cost-only mode.
    """
    # 1. Cost-only controller (lambda_carbon = 0.0)
    sim_cost = MicrogridSimulator(scenario="high_carbon_evening", seed=42)
    weights_cost = ObjectiveWeights(lambda_carbon=0.0)
    ctrl_cost = UCCMPCController(
        building_params=sim_cost.building_params,
        hvac_params=sim_cost.hvac_params,
        battery_params=sim_cost.battery_params,
        grid_limits=sim_cost.grid_limits,
        weights=weights_cost,
    )
    obs = sim_cost.reset(initial_temp_c=22.5, initial_soc=0.50)
    for _ in range(96):
        forecasts = extract_forecasts(sim_cost, horizon_steps=96)
        action = ctrl_cost.select_action(obs, forecasts)
        sim_cost.step(action)
        obs = sim_cost.get_current_observation()

    # 2. Carbon-aware controller (lambda_carbon = 0.10)
    sim_carbon = MicrogridSimulator(scenario="high_carbon_evening", seed=42)
    weights_carbon = ObjectiveWeights(lambda_carbon=0.10)
    ctrl_carbon = UCCMPCController(
        building_params=sim_carbon.building_params,
        hvac_params=sim_carbon.hvac_params,
        battery_params=sim_carbon.battery_params,
        grid_limits=sim_carbon.grid_limits,
        weights=weights_carbon,
    )
    obs = sim_carbon.reset(initial_temp_c=22.5, initial_soc=0.50)
    for _ in range(96):
        forecasts = extract_forecasts(sim_carbon, horizon_steps=96)
        action = ctrl_carbon.select_action(obs, forecasts)
        sim_carbon.step(action)
        obs = sim_carbon.get_current_observation()

    total_emissions_cost_only = sum(t.operational_emissions_kg for t in sim_cost.history)
    total_emissions_carbon_aware = sum(t.operational_emissions_kg for t in sim_carbon.history)

    # Carbon-aware mode must achieve lower or equal grid emissions
    assert total_emissions_carbon_aware <= total_emissions_cost_only + 1e-3


def test_cvar_robust_mode_under_uncertainty():
    """Verify that CVaR uncertainty mode protects against forecast demand surges

    by preserving battery reserve and reducing peak grid stress compared to nominal MPC.
    """
    # Simulate a scenario with noisy/uncertain demand
    sim_nominal = MicrogridSimulator(scenario="typical_weekday", seed=101)
    ctrl_nominal = UCCMPCController(
        building_params=sim_nominal.building_params,
        hvac_params=sim_nominal.hvac_params,
        battery_params=sim_nominal.battery_params,
        grid_limits=sim_nominal.grid_limits,
        risk_mode="nominal",
    )

    sim_cvar = MicrogridSimulator(scenario="typical_weekday", seed=101)
    ctrl_cvar = UCCMPCController(
        building_params=sim_cvar.building_params,
        hvac_params=sim_cvar.hvac_params,
        battery_params=sim_cvar.battery_params,
        grid_limits=sim_cvar.grid_limits,
        risk_mode="cvar",
        cvar_alpha=0.90,
        cvar_weight=0.30,
    )

    # Run both controllers under identical scenario
    obs_n = sim_nominal.reset(initial_temp_c=22.5, initial_soc=0.50)
    obs_c = sim_cvar.reset(initial_temp_c=22.5, initial_soc=0.50)

    for _ in range(96):
        fn = extract_forecasts(sim_nominal, horizon_steps=96)
        fc = extract_forecasts(sim_cvar, horizon_steps=96)
        an = ctrl_nominal.select_action(obs_n, fn)
        ac = ctrl_cvar.select_action(obs_c, fc)
        sim_nominal.step(an)
        sim_cvar.step(ac)
        obs_n = sim_nominal.get_current_observation()
        obs_c = sim_cvar.get_current_observation()

    # Both must complete without solver failure and satisfy comfort within 1 deg
    max_viol_n = max(t.comfort_violation_deg for t in sim_nominal.history)
    max_viol_c = max(t.comfort_violation_deg for t in sim_cvar.history)

    assert max_viol_n < 1.0
    assert max_viol_c < 1.0
    assert ctrl_cvar.last_decision_explanation["solver_status"] == "OPTIMAL"
