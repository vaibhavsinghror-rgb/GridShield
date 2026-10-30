"""Unified Microgrid Simulator.
Integrates Building, HVAC, BESS, Solar PV, EV fleet, Tariffs, and Carbon Accounting.
Maintains power balance, tracks physical constraints, and outputs comprehensive telemetry.
"""

from typing import Dict, Any, List, Optional
import numpy as np

from grid_sim.schemas import (
    BuildingThermalParams,
    HVACParams,
    BatteryParams,
    GridLimits,
    MicrogridAction,
    TelemetryStep,
)
from grid_sim.building import BuildingThermalZone
from grid_sim.hvac import HVACSystem
from grid_sim.battery import BatteryStorage
from grid_sim.ev_fleet import EVFleet
from grid_sim.solar import SolarPV
from grid_sim.tariffs import ElectricityTariff
from grid_sim.carbon import CarbonIntensityModel
from grid_sim.weather import ExogenousProfileGenerator


class MicrogridSimulator:
    def __init__(
        self,
        building_params: Optional[BuildingThermalParams] = None,
        hvac_params: Optional[HVACParams] = None,
        battery_params: Optional[BatteryParams] = None,
        grid_limits: Optional[GridLimits] = None,
        scenario: str = "typical_weekday",
        seed: int = 42,
        dt_hours: float = 0.25,
        lambda_carbon: float = 0.05,
        lambda_degradation: float = 0.015,
        lambda_comfort: float = 2.0,
        enable_ev: bool = False,
    ):
        self.dt_hours = dt_hours
        self.scenario = scenario
        self.seed = seed
        self.lambda_carbon = lambda_carbon
        self.lambda_degradation = lambda_degradation
        self.lambda_comfort = lambda_comfort

        self.building_params = building_params or BuildingThermalParams()
        self.hvac_params = hvac_params or HVACParams()
        self.battery_params = battery_params or BatteryParams()
        self.grid_limits = grid_limits or GridLimits()

        # Initialize physical sub-models
        self.building = BuildingThermalZone(self.building_params)
        self.hvac = HVACSystem(self.hvac_params)
        self.battery = BatteryStorage(self.battery_params)
        self.solar = SolarPV(installed_capacity_kw=40.0)
        self.ev_fleet = EVFleet(enabled=enable_ev)
        self.tariff = ElectricityTariff()
        self.carbon = CarbonIntensityModel(scenario=scenario)
        self.exogenous = ExogenousProfileGenerator(seed=seed, scenario=scenario)

        # Simulation state
        self.step_index = 0
        self.time_hours = 0.0
        self.history: List[TelemetryStep] = []

    def reset(self, initial_temp_c: float = 22.0, initial_soc: float = 0.50) -> Dict[str, Any]:
        """Resets the microgrid simulation to step 0."""
        self.step_index = 0
        self.time_hours = 0.0
        self.history.clear()

        self.building.reset(initial_temp_c=initial_temp_c)
        self.battery.reset(initial_soc=initial_soc)
        self.ev_fleet.reset()
        self.tariff.reset()

        return self.get_current_observation()

    def get_current_observation(self) -> Dict[str, Any]:
        """Returns the current state observable by a controller prior to taking an action."""
        exo = self.exogenous.get_conditions_at_time(self.time_hours)
        hour_of_day = self.time_hours % 24.0
        solar_gen = self.solar.generate(exo["solar_irradiance_kw_m2"])
        price = self.tariff.get_rate_at_hour(hour_of_day)
        carbon_intensity = self.carbon.get_intensity_at_hour(hour_of_day)

        return {
            "step": self.step_index,
            "time_hours": self.time_hours,
            "hour_of_day": hour_of_day,
            "indoor_temp_c": self.building.current_temp_c,
            "outdoor_temp_c": exo["outdoor_temp_c"],
            "solar_irradiance_kw_m2": exo["solar_irradiance_kw_m2"],
            "solar_generation_kw": solar_gen,
            "base_demand_kw": exo["base_demand_kw"],
            "occupancy": exo["occupancy"],
            "battery_soc": self.battery.soc,
            "battery_energy_kwh": self.battery.energy_kwh,
            "electricity_price": price,
            "carbon_intensity": carbon_intensity,
            "temp_min_comfort": self.building_params.temp_min_comfort_c,
            "temp_max_comfort": self.building_params.temp_max_comfort_c,
        }

    def step(self, action: MicrogridAction) -> TelemetryStep:
        """Executes one simulation step of length dt_hours."""
        exo = self.exogenous.get_conditions_at_time(self.time_hours)
        hour_of_day = self.time_hours % 24.0

        # 1. Dispatch HVAC system
        delivered_cool, delivered_heat, hvac_electric_kw = self.hvac.deliver(
            requested_cooling_thermal_kw=action.hvac_cooling_thermal_kw,
            requested_heating_thermal_kw=action.hvac_heating_thermal_kw,
        )

        # 2. Update Building Thermal Zone
        next_temp_c, q_internal, q_solar, comfort_viol_deg = self.building.step(
            outdoor_temp_c=exo["outdoor_temp_c"],
            solar_irradiance_kw_m2=exo["solar_irradiance_kw_m2"],
            occupancy=exo["occupancy"],
            cooling_thermal_kw=delivered_cool,
            heating_thermal_kw=delivered_heat,
            dt_hours=self.dt_hours,
        )

        # 3. Solar PV Generation
        solar_kw = self.solar.generate(exo["solar_irradiance_kw_m2"])

        # 4. Battery Storage Dispatch
        (
            charge_kw,
            discharge_kw,
            b_soc,
            b_kwh,
            degrad_cost,
        ) = self.battery.step(
            requested_charge_kw=action.battery_charge_kw,
            requested_discharge_kw=action.battery_discharge_kw,
            dt_hours=self.dt_hours,
        )

        # 5. EV Fleet Dispatch
        ev_charge_kw, ev_unmet_kwh, _ = self.ev_fleet.step(
            time_hours=self.time_hours,
            requested_charge_kw=action.ev_charge_kw,
            dt_hours=self.dt_hours,
        )

        # 6. Microgrid Power Balance:
        # P_grid = P_base + P_HVAC + P_charge + P_EV - P_discharge - P_solar
        net_load_kw = (
            exo["base_demand_kw"]
            + hvac_electric_kw
            + charge_kw
            + ev_charge_kw
            - discharge_kw
            - solar_kw
        )

        # Enforce physical grid inter-tie power limits
        # grid_power > 0 means importing from utility; grid_power < 0 means exporting
        grid_power_kw = max(
            -self.grid_limits.max_export_kw,
            min(self.grid_limits.max_import_kw, net_load_kw),
        )

        # 7. Electricity Tariffs and Energy Cost
        elec_price = self.tariff.get_rate_at_hour(hour_of_day)
        elec_cost = self.tariff.calculate_cost(
            grid_power_kw=grid_power_kw,
            dt_hours=self.dt_hours,
            hour_of_day=hour_of_day,
            export_tariff_ratio=self.grid_limits.export_tariff_ratio,
        )

        # 8. Operational Carbon Emissions
        carbon_intensity = self.carbon.get_intensity_at_hour(hour_of_day)
        emissions_kg = self.carbon.calculate_emissions(
            grid_power_kw=grid_power_kw,
            dt_hours=self.dt_hours,
            hour_of_day=hour_of_day,
            allow_export_credit=self.grid_limits.export_carbon_credit,
        )

        # 9. Unified Step Cost:
        # J_t = Cost + lambda_C * Emissions + lambda_D * Degradation + lambda_T * ComfortViolation
        comfort_penalty = comfort_viol_deg * self.dt_hours * self.lambda_comfort
        carbon_penalty = emissions_kg * self.lambda_carbon
        total_step_cost = elec_cost + carbon_penalty + degrad_cost + comfort_penalty

        telemetry = TelemetryStep(
            step=self.step_index,
            time_hours=self.time_hours,
            indoor_temp_c=next_temp_c,
            outdoor_temp_c=exo["outdoor_temp_c"],
            solar_irradiance_kw_m2=exo["solar_irradiance_kw_m2"],
            solar_generation_kw=solar_kw,
            base_demand_kw=exo["base_demand_kw"],
            occupancy_count=exo["occupancy"],
            hvac_cooling_thermal_kw=delivered_cool,
            hvac_heating_thermal_kw=delivered_heat,
            hvac_electric_kw=hvac_electric_kw,
            comfort_violation_deg=comfort_viol_deg,
            battery_soc=b_soc,
            battery_energy_kwh=b_kwh,
            battery_charge_kw=charge_kw,
            battery_discharge_kw=discharge_kw,
            battery_degradation_cost=degrad_cost,
            ev_charge_kw=ev_charge_kw,
            ev_energy_deficit_kwh=ev_unmet_kwh,
            grid_power_kw=grid_power_kw,
            electricity_price_per_kwh=elec_price,
            electricity_cost=elec_cost,
            carbon_intensity_gco2_per_kwh=carbon_intensity,
            operational_emissions_kg=emissions_kg,
            total_step_cost=total_step_cost,
        )

        self.history.append(telemetry)
        self.step_index += 1
        self.time_hours += self.dt_hours

        return telemetry
