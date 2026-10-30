"""Myopic (Single-Step) Linear Optimization Controller.
Solves an exact linear program for the immediate step t using SciPy linprog (HiGHS).
Serves as a classical local optimization baseline with no look-ahead horizon.
"""

from typing import Dict, Any, Optional
import numpy as np
from scipy.optimize import linprog

from grid_sim.schemas import (
    MicrogridAction,
    BuildingThermalParams,
    HVACParams,
    BatteryParams,
    GridLimits,
)
from optimization.objective import ObjectiveWeights
from optimization.safety_filter import ActionSafetyFilter


class MyopicController:
    def __init__(
        self,
        building_params: BuildingThermalParams,
        hvac_params: HVACParams,
        battery_params: BatteryParams,
        grid_limits: GridLimits,
        weights: Optional[ObjectiveWeights] = None,
        dt_hours: float = 0.25,
    ):
        self.building = building_params
        self.hvac = hvac_params
        self.battery = battery_params
        self.grid = grid_limits
        self.weights = weights or ObjectiveWeights()
        self.dt_hours = dt_hours
        self.safety_filter = ActionSafetyFilter(
            battery_params=battery_params,
            hvac_params=hvac_params,
            grid_limits=grid_limits,
            dt_hours=dt_hours,
        )

    def select_action(self, obs: Dict[str, Any]) -> MicrogridAction:
        """Formulates and solves a 1-step LP."""
        t_in = obs["indoor_temp_c"]
        t_out = obs["outdoor_temp_c"]
        solar_irrad = obs["solar_irradiance_kw_m2"]
        solar_gen = obs["solar_generation_kw"]
        base_demand = obs["base_demand_kw"]
        occupancy = obs["occupancy"]
        price = obs["electricity_price"]
        carbon_intensity = obs["carbon_intensity"]
        current_soc = obs["battery_soc"]
        current_e_kwh = current_soc * self.battery.capacity_kwh

        # Uncontrollable thermal gains
        q_int = self.building.internal_gain_base_kw + self.building.internal_gain_occupancy_multiplier * occupancy
        q_solar = self.building.solar_gain_factor * (solar_irrad * 100.0)
        q_envelope = self.building.ua_kw_per_c * (t_out - t_in)
        free_drift = (self.dt_hours / self.building.c_th_kwh_per_c) * (q_envelope + q_int + q_solar)
        alpha_t = self.dt_hours / self.building.c_th_kwh_per_c

        # Variables:
        # [0: Q_cool, 1: Q_heat, 2: P_c, 3: P_d, 4: P_imp, 5: P_exp, 6: s_high, 7: s_low]
        # Objective weights:
        cost_imp = (price + self.weights.lambda_carbon * (carbon_intensity / 1000.0)) * self.dt_hours
        cost_exp = -(price * self.grid.export_tariff_ratio + self.weights.lambda_carbon * (carbon_intensity / 1000.0)) * self.dt_hours
        cost_deg = self.weights.lambda_degradation * self.dt_hours
        cost_comfort = self.weights.lambda_comfort * self.dt_hours

        c = [
            0.0,              # Q_cool
            0.0,              # Q_heat
            cost_deg,         # P_c
            cost_deg,         # P_d
            cost_imp,         # P_imp
            cost_exp,         # P_exp
            cost_comfort,     # s_high
            cost_comfort,     # s_low
        ]

        # Bounds:
        bounds = [
            (0.0, self.hvac.cooling_capacity_thermal_kw),
            (0.0, self.hvac.heating_capacity_thermal_kw),
            (0.0, self.battery.max_charge_power_kw),
            (0.0, self.battery.max_discharge_power_kw),
            (0.0, self.grid.max_import_kw),
            (0.0, self.grid.max_export_kw),
            (0.0, None),
            (0.0, None),
        ]

        # Equality constraint: Power balance
        # (1/COP_cool)*Q_cool + (1/COP_heat)*Q_heat + P_c - P_d - P_imp + P_exp = P_solar - P_base
        A_eq = [[
            1.0 / self.hvac.cop_cooling,
            1.0 / self.hvac.cop_heating,
            1.0,
            -1.0,
            -1.0,
            1.0,
            0.0,
            0.0,
        ]]
        b_eq = [solar_gen - base_demand]

        # Inequality constraints: A_ub * x <= b_ub
        # 1. T_{t+1} - s_high <= T_max  ->  -alpha_t*Q_cool + alpha_t*Q_heat - s_high <= T_max - (T_in + free_drift)
        # 2. T_{t+1} + s_low >= T_min   ->  alpha_t*Q_cool - alpha_t*Q_heat - s_low <= (T_in + free_drift) - T_min
        # 3. E_{t+1} <= E_max           ->  eta_c*dt*P_c - (dt/eta_d)*P_d <= E_max - E_t
        # 4. E_{t+1} >= E_min           ->  -eta_c*dt*P_c + (dt/eta_d)*P_d <= E_t - E_min
        max_e = self.battery.soc_max * self.battery.capacity_kwh
        min_e = self.battery.soc_min * self.battery.capacity_kwh
        eta_c_dt = self.battery.charge_efficiency * self.dt_hours
        dt_div_eta_d = self.dt_hours / self.battery.discharge_efficiency

        A_ub = [
            [-alpha_t, alpha_t, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0],
            [alpha_t, -alpha_t, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0],
            [0.0, 0.0, eta_c_dt, -dt_div_eta_d, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, -eta_c_dt, dt_div_eta_d, 0.0, 0.0, 0.0, 0.0],
        ]
        b_ub = [
            self.building.temp_max_comfort_c - (t_in + free_drift),
            (t_in + free_drift) - self.building.temp_min_comfort_c,
            max_e - current_e_kwh,
            current_e_kwh - min_e,
        ]

        res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

        if res.success:
            q_cool = float(res.x[0])
            q_heat = float(res.x[1])
            p_c = float(res.x[2])
            p_d = float(res.x[3])
        else:
            # Fallback to zero dispatch if solver encounters an issue
            q_cool = 0.0
            q_heat = 0.0
            p_c = 0.0
            p_d = 0.0

        raw_action = MicrogridAction(
            hvac_cooling_thermal_kw=q_cool,
            hvac_heating_thermal_kw=q_heat,
            battery_charge_kw=p_c,
            battery_discharge_kw=p_d,
            ev_charge_kw=0.0,
        )

        filtered = self.safety_filter.validate_and_filter(
            action=raw_action,
            current_soc=current_soc,
            current_indoor_temp_c=t_in,
            solar_gen_kw=solar_gen,
            base_demand_kw=base_demand,
        )
        return filtered.action
