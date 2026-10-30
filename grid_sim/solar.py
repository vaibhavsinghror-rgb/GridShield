"""Photovoltaic Solar generation model.
Calculates electrical generation from global solar irradiance and system capacity.
"""


class SolarPV:
    def __init__(self, installed_capacity_kw: float = 40.0, inverter_efficiency: float = 0.95):
        self.installed_capacity_kw = installed_capacity_kw
        self.inverter_efficiency = inverter_efficiency

    def generate(self, irradiance_kw_m2: float) -> float:
        """Standard irradiance test condition is 1.0 kW/m².

        Returns electric power in kW.
        """
        # Linear PV model with inverter efficiency
        raw_power_kw = self.installed_capacity_kw * max(0.0, irradiance_kw_m2)
        ac_power_kw = raw_power_kw * self.inverter_efficiency
        return ac_power_kw
