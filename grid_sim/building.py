"""Single-zone Resistance-Capacitance (RC) building thermal model.
Implements the continuous/discrete thermal equation from Section 6.1:
T_{t+1} = T_t + (dt / C_th) * [ UA*(T_{o,t} - T_t) + Q_{int,t} + Q_{solar,t} - Q_{cool,t} + Q_{heat,t} ]
"""

from typing import Tuple
from grid_sim.schemas import BuildingThermalParams


class BuildingThermalZone:
    """Simulates zone temperature evolution under ambient weather, internal gains,

    solar gains, and HVAC cooling/heating.
    """

    def __init__(self, params: BuildingThermalParams, initial_temp_c: float = 22.0):
        self.params = params
        self.current_temp_c = initial_temp_c

    def step(
        self,
        outdoor_temp_c: float,
        solar_irradiance_kw_m2: float,
        occupancy: int,
        cooling_thermal_kw: float,
        heating_thermal_kw: float = 0.0,
        dt_hours: float = 0.25,
    ) -> Tuple[float, float, float, float]:
        """Advances thermal dynamics by dt_hours.

        Returns:
            next_temp_c: updated indoor temperature in °C.
            q_internal_kw: total internal heat gains in kW.
            q_solar_kw: solar thermal gain in kW.
            comfort_violation_deg: absolute excursion outside comfort band in °C.
        """
        # Internal gains: base equipment + occupants
        q_internal_kw = (
            self.params.internal_gain_base_kw
            + self.params.internal_gain_occupancy_multiplier * occupancy
        )

        # Solar heat gains through envelope / glazing
        # Scaled by solar gain factor (aperture proxy)
        q_solar_kw = self.params.solar_gain_factor * (solar_irradiance_kw_m2 * 100.0)

        # Heat transfer across building envelope: UA * (T_out - T_in)
        q_envelope_kw = self.params.ua_kw_per_c * (outdoor_temp_c - self.current_temp_c)

        # Net thermal rate of change in kW
        # cooling reduces heat (-), heating adds heat (+)
        net_thermal_power_kw = (
            q_envelope_kw
            + q_internal_kw
            + q_solar_kw
            - cooling_thermal_kw
            + heating_thermal_kw
        )

        # Discrete Euler update: dT = dt / C_th * net_thermal_power
        delta_temp_c = (dt_hours / self.params.c_th_kwh_per_c) * net_thermal_power_kw
        self.current_temp_c = self.current_temp_c + delta_temp_c

        # Calculate comfort violation: excursion outside [temp_min_comfort_c, temp_max_comfort_c]
        violation_deg = 0.0
        if self.current_temp_c < self.params.temp_min_comfort_c:
            violation_deg = self.params.temp_min_comfort_c - self.current_temp_c
        elif self.current_temp_c > self.params.temp_max_comfort_c:
            violation_deg = self.current_temp_c - self.params.temp_max_comfort_c

        return self.current_temp_c, q_internal_kw, q_solar_kw, violation_deg

    def reset(self, initial_temp_c: float = 22.0) -> None:
        self.current_temp_c = initial_temp_c
