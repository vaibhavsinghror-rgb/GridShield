"""Grid carbon intensity profile and operational emissions accounting.
Emissions (kgCO2) = Intensity (gCO2/kWh) * Energy (kWh) / 1000.
"""

from typing import Tuple


class CarbonIntensityModel:
    def __init__(
        self,
        base_clean_gco2: float = 80.0,
        shoulder_gco2: float = 220.0,
        peak_thermal_gco2: float = 450.0,
        scenario: str = "typical_weekday",
    ):
        self.base_clean_gco2 = base_clean_gco2
        self.shoulder_gco2 = shoulder_gco2
        self.peak_thermal_gco2 = peak_thermal_gco2
        self.scenario = scenario

    def get_intensity_at_hour(self, hour_of_day: float) -> float:
        """Returns grid carbon intensity in gCO2/kWh.
        Evening peaks (17:00-21:00) ramp up peaking fossil plants.
        Solar midday hours (10:00-15:00) feature clean renewable generation.
        """
        h = hour_of_day % 24.0
        if self.scenario == "high_carbon_evening" and 17.0 <= h < 22.0:
            return self.peak_thermal_gco2 * 1.35  # extreme peaking gas/coal grid

        if 17.0 <= h < 21.0:
            return self.peak_thermal_gco2
        elif 10.0 <= h < 15.0:
            return self.base_clean_gco2
        else:
            return self.shoulder_gco2

    def calculate_emissions(
        self,
        grid_power_kw: float,
        dt_hours: float,
        hour_of_day: float,
        allow_export_credit: bool = True,
    ) -> float:
        """Calculates operational emissions in kgCO2.
        For import: positive emissions.
        For export: offset avoided emissions if credit is enabled.
        """
        intensity_gco2_per_kwh = self.get_intensity_at_hour(hour_of_day)
        energy_kwh = grid_power_kw * dt_hours

        if energy_kwh >= 0.0:
            return (intensity_gco2_per_kwh * energy_kwh) / 1000.0
        else:
            if allow_export_credit:
                # Displacing grid fossil generation
                return (intensity_gco2_per_kwh * energy_kwh) / 1000.0
            else:
                return 0.0
