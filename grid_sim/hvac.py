"""HVAC System model relating delivered thermal energy to electrical energy via COP.
Enforces physical actuator capacity limits and derives electrical load.
"""

from typing import Tuple
from grid_sim.schemas import HVACParams


class HVACSystem:
    def __init__(self, params: HVACParams):
        self.params = params

    def deliver(
        self,
        requested_cooling_thermal_kw: float,
        requested_heating_thermal_kw: float = 0.0,
    ) -> Tuple[float, float, float]:
        """Clamps requested thermal powers to physical capacities and calculates electrical consumption.

        Returns:
            delivered_cooling_thermal_kw: delivered cooling in kW.
            delivered_heating_thermal_kw: delivered heating in kW.
            total_electric_power_kw: electrical power drawn by HVAC in kW.
        """
        # Physical actuator bounds
        cooling_thermal = max(
            0.0,
            min(requested_cooling_thermal_kw, self.params.cooling_capacity_thermal_kw),
        )
        heating_thermal = max(
            0.0,
            min(requested_heating_thermal_kw, self.params.heating_capacity_thermal_kw),
        )

        # Electrical power via Coefficient of Performance (COP)
        # Never equate thermal cooling directly to electric power
        electric_cooling = (
            cooling_thermal / self.params.cop_cooling
            if self.params.cop_cooling > 0
            else 0.0
        )
        electric_heating = (
            heating_thermal / self.params.cop_heating
            if self.params.cop_heating > 0
            else 0.0
        )

        total_electric_kw = electric_cooling + electric_heating
        return cooling_thermal, heating_thermal, total_electric_kw
