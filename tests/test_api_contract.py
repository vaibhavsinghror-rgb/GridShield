"""API Contract Verification Test.
Ensures schemas between Python optimization/simulation engine and TypeScript REST API match exactly.
"""

import pytest
from grid_sim.schemas import (
    MicrogridAction,
    TelemetryStep,
    BuildingThermalParams,
    HVACParams,
    BatteryParams,
)
from optimization.safety_filter import ActionSafetyFilter


def test_microgrid_action_contract():
    """Verify action payload matches TypeScript dispatch action contract."""
    action_dict = {
        "hvac_cooling_thermal_kw": 12.5,
        "hvac_heating_thermal_kw": 0.0,
        "battery_charge_kw": 5.0,
        "battery_discharge_kw": 0.0,
        "ev_charge_kw": 0.0,
    }
    action = MicrogridAction(**action_dict)
    serialized = action.model_dump()
    assert serialized["hvac_cooling_thermal_kw"] == 12.5
    assert serialized["battery_charge_kw"] == 5.0


def test_telemetry_schema_contract():
    """Verify telemetry serialization contains all required fields for dashboard."""
    telem_dict = {
        "step": 0,
        "time_hours": 0.0,
        "indoor_temp_c": 22.5,
        "outdoor_temp_c": 25.0,
        "solar_irradiance_kw_m2": 0.8,
        "solar_generation_kw": 30.4,
        "base_demand_kw": 12.0,
        "occupancy_count": 25,
        "hvac_cooling_thermal_kw": 10.0,
        "hvac_heating_thermal_kw": 0.0,
        "hvac_electric_kw": 2.857,
        "comfort_violation_deg": 0.0,
        "battery_soc": 0.65,
        "battery_energy_kwh": 65.0,
        "battery_charge_kw": 0.0,
        "battery_discharge_kw": 10.0,
        "battery_degradation_cost": 0.0375,
        "ev_charge_kw": 0.0,
        "ev_energy_deficit_kwh": 0.0,
        "grid_power_kw": 4.857,
        "electricity_price_per_kwh": 0.15,
        "electricity_cost": 0.182,
        "carbon_intensity_gco2_per_kwh": 220.0,
        "operational_emissions_kg": 0.267,
        "total_step_cost": 0.499,
    }
    step = TelemetryStep(**telem_dict)
    assert step.step == 0
    assert step.grid_power_kw == 4.857
