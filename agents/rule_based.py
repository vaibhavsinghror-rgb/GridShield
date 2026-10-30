"""Rule-Based Energy Management Baseline.
Applies intuitive heuristic dispatch policies:
- Pre-cools building before peak tariff window.
- Proportional HVAC cooling to keep temperature comfortably within 21.0 - 24.0°C.
- Charges battery during cheap off-peak hours (night) and during midday solar surplus.
- Discharges battery during expensive peak tariff hours and high carbon intensity.
"""

from typing import Dict, Any
from grid_sim.schemas import MicrogridAction, BatteryParams, BuildingThermalParams


class RuleBasedController:
    def __init__(
        self,
        target_temp_c: float = 22.0,
        temp_deadband_c: float = 0.5,
        peak_tariff_threshold: float = 0.25,
        offpeak_tariff_threshold: float = 0.10,
        high_carbon_threshold: float = 350.0,
    ):
        self.target_temp_c = target_temp_c
        self.temp_deadband_c = temp_deadband_c
        self.peak_tariff_threshold = peak_tariff_threshold
        self.offpeak_tariff_threshold = offpeak_tariff_threshold
        self.high_carbon_threshold = high_carbon_threshold

    def select_action(self, obs: Dict[str, Any]) -> MicrogridAction:
        """Determines control setpoints based on heuristic decision tree."""
        current_temp = obs["indoor_temp_c"]
        outdoor_temp = obs["outdoor_temp_c"]
        price = obs["electricity_price"]
        carbon_intensity = obs["carbon_intensity"]
        soc = obs["battery_soc"]
        solar_gen = obs["solar_generation_kw"]
        base_demand = obs["base_demand_kw"]
        hour = obs["hour_of_day"]

        # 1. HVAC Control Rule
        # Proportional cooling when temperature rises above target + deadband
        cool_thermal_kw = 0.0
        heat_thermal_kw = 0.0

        # Pre-cooling rule: If 15:00 - 17:00 (prior to peak tariff at 17:00), pre-cool to 21.5°C
        is_pre_cooling_window = (15.0 <= hour < 17.0)
        effective_target = 21.5 if is_pre_cooling_window else self.target_temp_c

        if current_temp > effective_target + self.temp_deadband_c:
            error = current_temp - effective_target
            # Proportional gain: ~12 kW thermal per degree error
            cool_thermal_kw = min(25.0, error * 12.0)
        elif current_temp < 21.0:
            # Heating if dropping below 21°C
            heat_thermal_kw = min(15.0, (21.5 - current_temp) * 10.0)

        # 2. Battery Dispatch Rule
        charge_kw = 0.0
        discharge_kw = 0.0

        # Estimated HVAC electric load
        est_hvac_electric = cool_thermal_kw / 3.5
        net_unserved_load = max(0.0, base_demand + est_hvac_electric - solar_gen)
        solar_surplus = max(0.0, solar_gen - (base_demand + est_hvac_electric))

        # Rule A: Solar surplus absorption (store green solar instead of exporting at low price)
        if solar_surplus > 1.0 and soc < 0.90:
            charge_kw = min(20.0, solar_surplus)

        # Rule B: Off-peak grid charging (cheap night electricity)
        elif price <= self.offpeak_tariff_threshold and soc < 0.85:
            charge_kw = 15.0

        # Rule C: Peak tariff / high carbon peak shaving (discharge to avoid grid import)
        elif (price >= self.peak_tariff_threshold or carbon_intensity >= self.high_carbon_threshold) and soc > 0.20:
            discharge_kw = min(20.0, net_unserved_load)

        return MicrogridAction(
            hvac_cooling_thermal_kw=cool_thermal_kw,
            hvac_heating_thermal_kw=heat_thermal_kw,
            battery_charge_kw=charge_kw,
            battery_discharge_kw=discharge_kw,
            ev_charge_kw=0.0,
        )
