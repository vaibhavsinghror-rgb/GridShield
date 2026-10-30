"""Physical schemas and data transfer objects for the GridShield microgrid simulator.
Explicit physical units are documented in every field.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BuildingThermalParams(BaseModel):
    c_th_kwh_per_c: float = Field(15.0, description="Effective thermal capacitance in kWh/°C")
    ua_kw_per_c: float = Field(1.2, description="Heat transfer coefficient in kW/°C")
    internal_gain_base_kw: float = Field(2.0, description="Base internal heat gain in kW")
    internal_gain_occupancy_multiplier: float = Field(0.1, description="Heat gain per occupant in kW")
    solar_gain_factor: float = Field(0.15, description="Fraction of solar irradiance converted to zone heat")
    temp_min_comfort_c: float = Field(21.0, description="Lower comfort band temperature in °C")
    temp_max_comfort_c: float = Field(24.0, description="Upper comfort band temperature in °C")
    temp_target_c: float = Field(22.5, description="Target comfort temperature in °C")


class HVACParams(BaseModel):
    cooling_capacity_thermal_kw: float = Field(30.0, description="Maximum cooling thermal power in kW")
    heating_capacity_thermal_kw: float = Field(20.0, description="Maximum heating thermal power in kW")
    cop_cooling: float = Field(3.5, description="Cooling Coefficient of Performance")
    cop_heating: float = Field(3.0, description="Heating Coefficient of Performance")


class BatteryParams(BaseModel):
    capacity_kwh: float = Field(100.0, description="Nominal battery storage capacity in kWh")
    soc_min: float = Field(0.10, description="Minimum allowable state of charge (fraction [0, 1])")
    soc_max: float = Field(0.95, description="Maximum allowable state of charge (fraction [0, 1])")
    soc_initial: float = Field(0.50, description="Initial state of charge (fraction [0, 1])")
    max_charge_power_kw: float = Field(25.0, description="Maximum charging rate in kW")
    max_discharge_power_kw: float = Field(25.0, description="Maximum discharging rate in kW")
    charge_efficiency: float = Field(0.92, description="Round-trip charge efficiency fraction")
    discharge_efficiency: float = Field(0.92, description="Round-trip discharge efficiency fraction")
    degradation_cost_per_kwh_throughput: float = Field(0.015, description="Cost proxy per kWh energy throughput ($/kWh)")


class GridLimits(BaseModel):
    max_import_kw: float = Field(100.0, description="Maximum grid import power in kW")
    max_export_kw: float = Field(50.0, description="Maximum grid export power in kW")
    export_tariff_ratio: float = Field(0.50, description="Export price multiplier relative to import tariff")
    export_carbon_credit: bool = Field(True, description="Whether exports offset operational grid emissions")


class MicrogridAction(BaseModel):
    """Control setpoints requested for the current timestep."""
    hvac_cooling_thermal_kw: float = Field(0.0, description="Requested cooling thermal power in kW [0, P_max]")
    hvac_heating_thermal_kw: float = Field(0.0, description="Requested heating thermal power in kW [0, P_max]")
    battery_charge_kw: float = Field(0.0, description="Requested battery charge power in kW [0, P_max]")
    battery_discharge_kw: float = Field(0.0, description="Requested battery discharge power in kW [0, P_max]")
    ev_charge_kw: float = Field(0.0, description="Requested EV fleet charging power in kW [0, P_max]")


class TelemetryStep(BaseModel):
    """Complete physical telemetry at the end of a simulation timestep."""
    step: int = Field(..., description="Timestep index")
    time_hours: float = Field(..., description="Elapsed simulation time in hours")
    indoor_temp_c: float = Field(..., description="Indoor temperature at end of step in °C")
    outdoor_temp_c: float = Field(..., description="Outdoor ambient temperature in °C")
    solar_irradiance_kw_m2: float = Field(..., description="Global solar irradiance in kW/m²")
    solar_generation_kw: float = Field(..., description="Solar PV electric power output in kW")
    base_demand_kw: float = Field(..., description="Non-HVAC building base electric demand in kW")
    occupancy_count: int = Field(..., description="Number of building occupants")
    
    # HVAC
    hvac_cooling_thermal_kw: float = Field(..., description="Delivered cooling thermal output in kW")
    hvac_heating_thermal_kw: float = Field(..., description="Delivered heating thermal output in kW")
    hvac_electric_kw: float = Field(..., description="Total HVAC electrical power consumption in kW")
    comfort_violation_deg: float = Field(..., description="Temperature deviation outside [21, 24]°C comfort band in °C")
    
    # Battery
    battery_soc: float = Field(..., description="Battery state of charge [0, 1]")
    battery_energy_kwh: float = Field(..., description="Stored battery energy in kWh")
    battery_charge_kw: float = Field(..., description="Delivered battery charge power in kW")
    battery_discharge_kw: float = Field(..., description="Delivered battery discharge power in kW")
    battery_degradation_cost: float = Field(..., description="Estimated degradation cost this step in USD")
    
    # EV
    ev_charge_kw: float = Field(0.0, description="Delivered EV charging power in kW")
    ev_energy_deficit_kwh: float = Field(0.0, description="Unmet EV departure energy in kWh")
    
    # Grid & Cost
    grid_power_kw: float = Field(..., description="Net power at grid point: >0 import, <0 export in kW")
    electricity_price_per_kwh: float = Field(..., description="Effective electricity tariff in $/kWh")
    electricity_cost: float = Field(..., description="Electricity cost this step in USD")
    carbon_intensity_gco2_per_kwh: float = Field(..., description="Grid carbon intensity in gCO2/kWh")
    operational_emissions_kg: float = Field(..., description="Operational emissions this step in kgCO2")
    total_step_cost: float = Field(..., description="Unified cost (electricity + carbon + degradation + comfort penalty) in USD")
