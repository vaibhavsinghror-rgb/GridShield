"""Rigorous automated tests for physical microgrid dynamics.
Verifies conservation laws, thermodynamic state updates against analytical hand calculations,
efficiency losses, power balance, and reproducible determinism.
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
from grid_sim.building import BuildingThermalZone
from grid_sim.hvac import HVACSystem
from grid_sim.battery import BatteryStorage
from grid_sim.microgrid import MicrogridSimulator


def test_thermal_update_hand_calculation():
    """Verify building thermal equation against exact analytical step:
    T_{t+1} = T_t + (dt / C_th) * [ UA*(T_out - T_in) + Q_int + Q_solar - Q_cool + Q_heat ]
    """
    params = BuildingThermalParams(
        c_th_kwh_per_c=10.0,
        ua_kw_per_c=1.0,
        internal_gain_base_kw=2.0,
        internal_gain_occupancy_multiplier=0.1,
        solar_gain_factor=0.10,
    )
    zone = BuildingThermalZone(params, initial_temp_c=22.0)

    # Inputs:
    # T_in = 22.0, T_out = 32.0, dt = 0.25 h
    # Occupancy = 10 -> Q_int = 2.0 + 0.1 * 10 = 3.0 kW
    # Irradiance = 0.5 kW/m2 -> Q_solar = 0.10 * (0.5 * 100) = 5.0 kW
    # Envelope UA*(T_out - T_in) = 1.0 * (32.0 - 22.0) = 10.0 kW
    # Q_cool = 8.0 kW, Q_heat = 0.0 kW
    # Net thermal power = 10.0 + 3.0 + 5.0 - 8.0 = 10.0 kW
    # dT = (0.25 / 10.0) * 10.0 = +0.25 °C
    # Expected T_{t+1} = 22.0 + 0.25 = 22.25 °C
    next_temp, q_int, q_solar, comfort_viol = zone.step(
        outdoor_temp_c=32.0,
        solar_irradiance_kw_m2=0.5,
        occupancy=10,
        cooling_thermal_kw=8.0,
        heating_thermal_kw=0.0,
        dt_hours=0.25,
    )

    assert pytest.approx(next_temp, rel=1e-5) == 22.25
    assert pytest.approx(q_int, rel=1e-5) == 3.0
    assert pytest.approx(q_solar, rel=1e-5) == 5.0
    assert comfort_viol == 0.0  # inside [21, 24]


def test_hvac_cop_electric_conversion():
    """Verify that delivered thermal output is coupled to electric power via COP:
    P_electric = Q_cool / COP_cool
    """
    params = HVACParams(
        cooling_capacity_thermal_kw=30.0,
        cop_cooling=3.5,
    )
    hvac = HVACSystem(params)

    # Request 14 kW thermal cooling
    # Expected electric = 14 / 3.5 = 4.0 kW
    cool, heat, p_elec = hvac.deliver(requested_cooling_thermal_kw=14.0)
    assert cool == 14.0
    assert pytest.approx(p_elec, rel=1e-5) == 4.0

    # Request exceeding capacity (e.g. 50 kW) clamped to 30 kW
    # Expected electric = 30 / 3.5 = 8.5714 kW
    cool_clamped, _, p_elec_clamped = hvac.deliver(requested_cooling_thermal_kw=50.0)
    assert cool_clamped == 30.0
    assert pytest.approx(p_elec_clamped, rel=1e-4) == 30.0 / 3.5


def test_battery_charge_efficiency_and_limits():
    """Verify BESS state update:
    E_{t+1} = E_t + eta_c * P_c * dt
    """
    params = BatteryParams(
        capacity_kwh=100.0,
        soc_initial=0.50,
        soc_min=0.10,
        soc_max=0.95,
        max_charge_power_kw=20.0,
        charge_efficiency=0.90,
    )
    battery = BatteryStorage(params)
    assert battery.energy_kwh == 50.0

    # Charge at 20 kW for 0.25 h
    # Stored energy increase = 0.90 * 20.0 * 0.25 = 4.5 kWh
    # Expected E_{t+1} = 54.5 kWh, SoC = 0.545
    p_c, p_d, soc, e_kwh, deg_cost = battery.step(
        requested_charge_kw=20.0,
        requested_discharge_kw=0.0,
        dt_hours=0.25,
    )
    assert p_c == 20.0
    assert p_d == 0.0
    assert pytest.approx(e_kwh, rel=1e-5) == 54.5
    assert pytest.approx(soc, rel=1e-5) == 0.545


def test_battery_mutual_exclusion():
    """Verify that simultaneous charge and discharge requests are mutually excluded."""
    params = BatteryParams(
        capacity_kwh=100.0,
        soc_initial=0.50,
        max_charge_power_kw=25.0,
        max_discharge_power_kw=25.0,
    )
    battery = BatteryStorage(params)

    # Request both 20 kW charge and 10 kW discharge
    # Net request is +10 kW charge, discharge must be 0
    p_c, p_d, _, _, _ = battery.step(
        requested_charge_kw=20.0,
        requested_discharge_kw=10.0,
        dt_hours=0.25,
    )
    assert p_c > 0.0
    assert p_d == 0.0


def test_microgrid_power_balance():
    """Verify exact microgrid power balance:
    P_grid = P_base + P_HVAC + P_c + P_EV - P_d - P_solar
    """
    sim = MicrogridSimulator(scenario="typical_weekday", seed=42)
    obs = sim.reset(initial_temp_c=22.0, initial_soc=0.50)

    # Action: cooling 7 kW thermal (electric = 7 / 3.5 = 2.0 kW)
    # Battery charge 10 kW
    action = MicrogridAction(
        hvac_cooling_thermal_kw=7.0,
        battery_charge_kw=10.0,
        battery_discharge_kw=0.0,
    )
    step_telemetry = sim.step(action)

    expected_p_grid = (
        step_telemetry.base_demand_kw
        + step_telemetry.hvac_electric_kw
        + step_telemetry.battery_charge_kw
        + step_telemetry.ev_charge_kw
        - step_telemetry.battery_discharge_kw
        - step_telemetry.solar_generation_kw
    )
    assert pytest.approx(step_telemetry.grid_power_kw, rel=1e-4) == expected_p_grid


def test_simulator_24h_episode_reproducibility():
    """WP1 Gate: The simulator runs an entire 24-hour episode (96 steps),
    logs full telemetry, and is perfectly reproducible with fixed seed.
    """
    sim1 = MicrogridSimulator(scenario="typical_weekday", seed=101)
    sim2 = MicrogridSimulator(scenario="typical_weekday", seed=101)

    sim1.reset()
    sim2.reset()

    action = MicrogridAction(hvac_cooling_thermal_kw=5.0, battery_charge_kw=5.0)

    for _ in range(96):  # 24 hours at 15-min intervals
        t1 = sim1.step(action)
        t2 = sim2.step(action)
        assert t1.indoor_temp_c == t2.indoor_temp_c
        assert t1.grid_power_kw == t2.grid_power_kw
        assert t1.total_step_cost == t2.total_step_cost

    assert len(sim1.history) == 96
    assert sim1.time_hours == 24.0
