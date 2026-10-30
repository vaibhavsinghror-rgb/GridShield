"""Optional Electric Vehicle (EV) fleet charging model.
Tracks EV availability windows, charging requests, and departure energy deficits.
"""

from typing import Tuple, Dict, Any


class EVFleet:
    def __init__(
        self,
        enabled: bool = False,
        charger_max_kw: float = 7.2,
        battery_capacity_kwh: float = 50.0,
        arrival_hour: float = 8.0,
        departure_hour: float = 17.0,
        target_departure_kwh: float = 40.0,
        initial_arrival_kwh: float = 15.0,
    ):
        self.enabled = enabled
        self.charger_max_kw = charger_max_kw
        self.battery_capacity_kwh = battery_capacity_kwh
        self.arrival_hour = arrival_hour
        self.departure_hour = departure_hour
        self.target_departure_kwh = target_departure_kwh
        self.initial_arrival_kwh = initial_arrival_kwh
        self.current_kwh = 0.0
        self.is_connected = False
        self.unmet_energy_kwh = 0.0

    def step(
        self,
        time_hours: float,
        requested_charge_kw: float,
        dt_hours: float = 0.25,
    ) -> Tuple[float, float, bool]:
        """Dispatches EV charging if vehicle is connected.

        Returns:
            delivered_charge_kw: actual delivered EV charging power in kW.
            unmet_energy_kwh: shortfall at or after departure in kWh.
            is_connected: whether EV is physically plugged in.
        """
        if not self.enabled:
            return 0.0, 0.0, False

        day_hour = time_hours % 24.0

        # Arrival event
        if abs(day_hour - self.arrival_hour) < (dt_hours / 2.0):
            self.is_connected = True
            self.current_kwh = self.initial_arrival_kwh
            self.unmet_energy_kwh = 0.0

        # Charging window
        if self.arrival_hour <= day_hour < self.departure_hour and self.is_connected:
            max_p = min(requested_charge_kw, self.charger_max_kw)
            headroom = max(0.0, self.battery_capacity_kwh - self.current_kwh)
            delivered_kw = min(max_p, headroom / dt_hours)
            self.current_kwh += delivered_kw * dt_hours
            return delivered_kw, 0.0, True

        # Departure event
        if abs(day_hour - self.departure_hour) < (dt_hours / 2.0) and self.is_connected:
            self.unmet_energy_kwh = max(0.0, self.target_departure_kwh - self.current_kwh)
            self.is_connected = False
            return 0.0, self.unmet_energy_kwh, False

        return 0.0, self.unmet_energy_kwh, False

    def reset(self) -> None:
        self.current_kwh = 0.0
        self.is_connected = False
        self.unmet_energy_kwh = 0.0
