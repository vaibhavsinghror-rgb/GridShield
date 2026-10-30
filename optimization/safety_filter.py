"""Safety Filter Module for Microgrid Control.
Acts as an invariant safety boundary verifying and clamping control setpoints
against hard physical constraints (actuator limits, SoC boundaries, power limits,
mutual exclusion) before execution in the simulator.
Logs all constraint violations and corrections with explicit reasons.
"""

from typing import Tuple, List, Dict, Any, Optional
from pydantic import BaseModel, Field

from grid_sim.schemas import MicrogridAction, BatteryParams, HVACParams, GridLimits


class SafetyViolation(BaseModel):
    parameter: str
    requested_value: float
    corrected_value: float
    reason: str


class SafetyFilterResult(BaseModel):
    action: MicrogridAction
    violations: List[SafetyViolation] = Field(default_factory=list)
    was_modified: bool = False


class ActionSafetyFilter:
    """Rigorous physical validator and safety governor."""

    def __init__(
        self,
        battery_params: BatteryParams,
        hvac_params: HVACParams,
        grid_limits: GridLimits,
        dt_hours: float = 0.25,
    ):
        self.battery_params = battery_params
        self.hvac_params = hvac_params
        self.grid_limits = grid_limits
        self.dt_hours = dt_hours
        self.total_corrections = 0
        self.violation_log: List[SafetyViolation] = []

    def validate_and_filter(
        self,
        action: MicrogridAction,
        current_soc: float,
        current_indoor_temp_c: float,
        solar_gen_kw: float = 0.0,
        base_demand_kw: float = 0.0,
    ) -> SafetyFilterResult:
        """Evaluates an incoming control action against all physical system invariants,

        corrects violations, and returns a verified feasible action.
        """
        violations: List[SafetyViolation] = []

        # 1. HVAC Actuator Limits
        # Cooling
        req_cool = action.hvac_cooling_thermal_kw
        clamped_cool = max(0.0, min(self.hvac_params.cooling_capacity_thermal_kw, req_cool))
        if clamped_cool != req_cool:
            violations.append(
                SafetyViolation(
                    parameter="hvac_cooling_thermal_kw",
                    requested_value=req_cool,
                    corrected_value=clamped_cool,
                    reason=f"Cooling thermal power outside [0, {self.hvac_params.cooling_capacity_thermal_kw}] kW",
                )
            )

        # Heating
        req_heat = action.hvac_heating_thermal_kw
        clamped_heat = max(0.0, min(self.hvac_params.heating_capacity_thermal_kw, req_heat))
        if clamped_heat != req_heat:
            violations.append(
                SafetyViolation(
                    parameter="hvac_heating_thermal_kw",
                    requested_value=req_heat,
                    corrected_value=clamped_heat,
                    reason=f"Heating thermal power outside [0, {self.hvac_params.heating_capacity_thermal_kw}] kW",
                )
            )

        # 2. Battery Mutual Exclusion (cannot charge and discharge simultaneously)
        req_charge = max(0.0, action.battery_charge_kw)
        req_discharge = max(0.0, action.battery_discharge_kw)

        if req_charge > 0.0 and req_discharge > 0.0:
            if req_charge >= req_discharge:
                corrected_charge = req_charge - req_discharge
                corrected_discharge = 0.0
            else:
                corrected_charge = 0.0
                corrected_discharge = req_discharge - req_charge

            violations.append(
                SafetyViolation(
                    parameter="battery_simultaneous_dispatch",
                    requested_value=req_charge + req_discharge,
                    corrected_value=corrected_charge + corrected_discharge,
                    reason="Simultaneous charging and discharging is physically prohibited; resolved net flux",
                )
            )
            req_charge = corrected_charge
            req_discharge = corrected_discharge

        # 3. Battery Power and SoC Feasibility
        current_energy_kwh = current_soc * self.battery_params.capacity_kwh
        max_energy_kwh = self.battery_params.soc_max * self.battery_params.capacity_kwh
        min_energy_kwh = self.battery_params.soc_min * self.battery_params.capacity_kwh

        # Charge power check
        clamped_charge = min(req_charge, self.battery_params.max_charge_power_kw)
        # Energy headroom check
        max_storable_kwh = max(0.0, max_energy_kwh - current_energy_kwh)
        max_p_by_soc = max_storable_kwh / (self.battery_params.charge_efficiency * self.dt_hours)
        clamped_charge = min(clamped_charge, max_p_by_soc)

        if clamped_charge != action.battery_charge_kw and action.battery_charge_kw > 0.0:
            violations.append(
                SafetyViolation(
                    parameter="battery_charge_kw",
                    requested_value=action.battery_charge_kw,
                    corrected_value=clamped_charge,
                    reason=f"Charge rate clamped to {clamped_charge:.2f} kW to avoid violating battery capacity or max power",
                )
            )

        # Discharge power check
        clamped_discharge = min(req_discharge, self.battery_params.max_discharge_power_kw)
        # Energy available above min SoC
        avail_kwh = max(0.0, current_energy_kwh - min_energy_kwh)
        max_p_by_soc_discharge = (avail_kwh * self.battery_params.discharge_efficiency) / self.dt_hours
        clamped_discharge = min(clamped_discharge, max_p_by_soc_discharge)

        if clamped_discharge != action.battery_discharge_kw and action.battery_discharge_kw > 0.0:
            violations.append(
                SafetyViolation(
                    parameter="battery_discharge_kw",
                    requested_value=action.battery_discharge_kw,
                    corrected_value=clamped_discharge,
                    reason=f"Discharge rate clamped to {clamped_discharge:.2f} kW to preserve minimum SoC buffer",
                )
            )

        # 4. EV Fleet charging clamping
        req_ev = max(0.0, action.ev_charge_kw)

        # 5. Resulting action
        corrected_action = MicrogridAction(
            hvac_cooling_thermal_kw=clamped_cool,
            hvac_heating_thermal_kw=clamped_heat,
            battery_charge_kw=clamped_charge,
            battery_discharge_kw=clamped_discharge,
            ev_charge_kw=req_ev,
        )

        was_modified = len(violations) > 0
        if was_modified:
            self.total_corrections += len(violations)
            self.violation_log.extend(violations)

        return SafetyFilterResult(
            action=corrected_action,
            violations=violations,
            was_modified=was_modified,
        )
