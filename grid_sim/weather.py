"""Deterministic weather, occupancy, and base demand profile generators.
Supports seasonal variation, heatwaves, and configurable scenarios.
"""

import math
import numpy as np
from typing import Dict, Any, Tuple


class WeatherGenerator:
    """Generates synthetic outdoor temperature and solar irradiance for microgrid simulation."""

    def __init__(self, seed: int = 42, scenario: str = "typical_weekday"):
        self.seed = seed
        self.scenario = scenario
        self.rng = np.random.default_rng(seed)

    def get_weather_at_time(self, time_hours: float) -> Tuple[float, float]:
        """Returns (outdoor_temp_c, solar_irradiance_kw_m2) at simulation time_hours."""
        hour_of_day = time_hours % 24.0

        # Base diurnal temperature profile peaking around 15:00
        # Typical diurnal cycle: min at 05:00, max at 15:00
        temp_phase = (hour_of_day - 15.0) * (2.0 * math.pi / 24.0)

        if self.scenario == "hot_summer_day":
            base_temp = 32.0
            temp_swing = 8.0  # reaches 40°C in afternoon
        elif self.scenario == "solar_surplus":
            base_temp = 25.0
            temp_swing = 6.0
        elif self.scenario == "high_carbon_evening":
            base_temp = 22.0
            temp_swing = 5.0
        else:  # typical_weekday or weekend
            base_temp = 24.0
            temp_swing = 6.0

        outdoor_temp = base_temp + temp_swing * math.cos(temp_phase)

        # Solar irradiance (clearsky bell curve between ~06:00 and 18:00)
        solar_irradiance = 0.0
        if 6.0 <= hour_of_day <= 18.0:
            solar_phase = (hour_of_day - 12.0) * (math.pi / 12.0)
            clearsky_peak = 1.0 if self.scenario == "solar_surplus" else 0.85
            solar_irradiance = max(0.0, clearsky_peak * math.cos(solar_phase))

        return outdoor_temp, solar_irradiance


class ExogenousProfileGenerator:
    """Generates occupancy, non-HVAC base building demand, tariffs, and carbon intensity."""

    def __init__(self, seed: int = 42, scenario: str = "typical_weekday"):
        self.seed = seed
        self.scenario = scenario
        self.weather = WeatherGenerator(seed=seed, scenario=scenario)

    def get_conditions_at_time(self, time_hours: float) -> Dict[str, Any]:
        hour_of_day = time_hours % 24.0
        outdoor_temp, solar_irradiance = self.weather.get_weather_at_time(time_hours)

        # Occupancy model
        is_weekend = self.scenario == "weekend"
        if is_weekend:
            occupancy = 5 if 10.0 <= hour_of_day <= 18.0 else 0
        else:
            if 8.0 <= hour_of_day <= 17.0:
                occupancy = 40
            elif 17.0 < hour_of_day <= 20.0:
                occupancy = 15
            else:
                occupancy = 2

        # Non-HVAC base electrical demand (lighting, computers, appliances)
        # Base baseload: 8 kW
        base_load_kw = 8.0 + 0.3 * occupancy
        if 9.0 <= hour_of_day <= 17.0:
            base_load_kw += 5.0  # business operations

        return {
            "time_hours": time_hours,
            "outdoor_temp_c": outdoor_temp,
            "solar_irradiance_kw_m2": solar_irradiance,
            "occupancy": occupancy,
            "base_demand_kw": base_load_kw,
        }
