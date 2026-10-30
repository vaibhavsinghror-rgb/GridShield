"""Battery Energy Storage System (BESS) simulator.
Enforces physical SoC limits, charge/discharge rates, efficiency losses,
and mutual exclusion of charging and discharging.
"""

from typing import Tuple
from grid_sim.schemas import BatteryParams


class BatteryStorage:
    def __init__(self, params: BatteryParams):
        self.params = params
        self.soc = params.soc_initial
        self.energy_kwh = self.soc * params.capacity_kwh
        self.total_throughput_kwh = 0.0

    @property
    def min_energy_kwh(self) -> float:
        return self.params.soc_min * self.params.capacity_kwh

    @property
    def max_energy_kwh(self) -> float:
        return self.params.soc_max * self.params.capacity_kwh

    def step(
        self,
        requested_charge_kw: float,
        requested_discharge_kw: float,
        dt_hours: float = 0.25,
    ) -> Tuple[float, float, float, float, float]:
        """Dispatches battery power with physical clamping, efficiency losses,
        and throughput degradation.

        Returns:
            delivered_charge_kw: actual delivered charging power in kW.
            delivered_discharge_kw: actual delivered discharging power in kW.
            next_soc: updated state of charge [0, 1].
            next_energy_kwh: updated stored energy in kWh.
            degradation_cost: estimated degradation cost for this step in USD.
        """
        # Mutual exclusion: if both are requested, take the dominant direction or zero
        if requested_charge_kw > 0.0 and requested_discharge_kw > 0.0:
            net_requested = requested_charge_kw - requested_discharge_kw
            if net_requested > 0.0:
                requested_charge_kw = net_requested
                requested_discharge_kw = 0.0
            else:
                requested_discharge_kw = -net_requested
                requested_charge_kw = 0.0

        delivered_charge_kw = 0.0
        delivered_discharge_kw = 0.0

        if requested_charge_kw > 0.0:
            # Power limit
            p_charge = min(requested_charge_kw, self.params.max_charge_power_kw)
            # Energy capacity headroom considering charging efficiency
            max_storable_kwh = max(0.0, self.max_energy_kwh - self.energy_kwh)
            max_p_by_energy = max_storable_kwh / (self.params.charge_efficiency * dt_hours)
            delivered_charge_kw = min(p_charge, max_p_by_energy)
            delivered_discharge_kw = 0.0

        elif requested_discharge_kw > 0.0:
            # Power limit
            p_discharge = min(requested_discharge_kw, self.params.max_discharge_power_kw)
            # Energy available above min SoC considering discharge efficiency
            avail_kwh = max(0.0, self.energy_kwh - self.min_energy_kwh)
            max_p_by_energy = (avail_kwh * self.params.discharge_efficiency) / dt_hours
            delivered_discharge_kw = min(p_discharge, max_p_by_energy)
            delivered_charge_kw = 0.0

        # State of charge update
        # E_{t+1} = E_t + eta_c * P_c * dt - (P_d * dt) / eta_d
        delta_energy = (
            self.params.charge_efficiency * delivered_charge_kw * dt_hours
            - (delivered_discharge_kw * dt_hours) / self.params.discharge_efficiency
        )
        self.energy_kwh = max(
            self.min_energy_kwh,
            min(self.max_energy_kwh, self.energy_kwh + delta_energy),
        )
        self.soc = self.energy_kwh / self.params.capacity_kwh

        # Degradation proxy based on gross throughput
        step_throughput = (delivered_charge_kw + delivered_discharge_kw) * dt_hours
        self.total_throughput_kwh += step_throughput
        degradation_cost = (
            step_throughput * self.params.degradation_cost_per_kwh_throughput
        )

        return (
            delivered_charge_kw,
            delivered_discharge_kw,
            self.soc,
            self.energy_kwh,
            degradation_cost,
        )

    def reset(self, initial_soc: float = None) -> None:
        if initial_soc is not None:
            self.soc = max(self.params.soc_min, min(self.params.soc_max, initial_soc))
        else:
            self.soc = self.params.soc_initial
        self.energy_kwh = self.soc * self.params.capacity_kwh
        self.total_throughput_kwh = 0.0
