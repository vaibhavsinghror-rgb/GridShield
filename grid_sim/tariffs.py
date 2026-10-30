"""Time-Of-Use (TOU) electricity tariff structure and cost calculations.
Separates volumetric energy charges from monthly peak demand charges.
"""

from typing import Dict, Any, List


class ElectricityTariff:
    def __init__(
        self,
        off_peak_rate: float = 0.08,
        shoulder_rate: float = 0.15,
        peak_rate: float = 0.32,
        demand_charge_per_kw: float = 12.0,
        currency: str = "USD",
    ):
        self.off_peak_rate = off_peak_rate
        self.shoulder_rate = shoulder_rate
        self.peak_rate = peak_rate
        self.demand_charge_per_kw = demand_charge_per_kw
        self.currency = currency
        self.peak_demand_kw = 0.0

    def get_rate_at_hour(self, hour_of_day: float) -> float:
        """Determines $/kWh rate based on time of day.
        Off-peak: 22:00 - 07:00
        Shoulder: 07:00 - 17:00, 21:00 - 22:00
        Peak: 17:00 - 21:00
        """
        h = hour_of_day % 24.0
        if 17.0 <= h < 21.0:
            return self.peak_rate
        elif (7.0 <= h < 17.0) or (21.0 <= h < 22.0):
            return self.shoulder_rate
        else:
            return self.off_peak_rate

    def calculate_cost(
        self,
        grid_power_kw: float,
        dt_hours: float,
        hour_of_day: float,
        export_tariff_ratio: float = 0.50,
    ) -> float:
        """Calculates energy cost in USD for the timestep.
        grid_power_kw > 0 is import; grid_power_kw < 0 is export.
        """
        rate = self.get_rate_at_hour(hour_of_day)
        if grid_power_kw >= 0.0:
            cost = grid_power_kw * dt_hours * rate
            self.peak_demand_kw = max(self.peak_demand_kw, grid_power_kw)
        else:
            # Export compensation
            export_kw = -grid_power_kw
            cost = -(export_kw * dt_hours * (rate * export_tariff_ratio))
        return cost

    def reset(self) -> None:
        self.peak_demand_kw = 0.0
