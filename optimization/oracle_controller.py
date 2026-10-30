"""Perfect-Information Oracle Benchmark Controller.
Formulates and solves a multi-period global linear program using future realized signals.
Serves as an idealized theoretical lower-bound benchmark.
Non-causal: Never exposed to deployable real-time controllers.
"""

from typing import Dict, Any, List, Optional
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


class PerfectInformationOracle:
    def __init__(
        self,
        building_params: BuildingThermalParams,
        hvac_params: HVACParams,
        battery_params: BatteryParams,
        grid_limits: GridLimits,
        weights: Optional[ObjectiveWeights] = None,
        dt_hours: float = 0.25,
        horizon_steps: int = 96,
    ):
        self.building = building_params
        self.hvac = hvac_params
        self.battery = battery_params
        self.grid = grid_limits
        self.weights = weights or ObjectiveWeights()
        self.dt_hours = dt_hours
        self.horizon_steps = horizon_steps
        self.safety_filter = ActionSafetyFilter(
            battery_params=battery_params,
            hvac_params=hvac_params,
            grid_limits=grid_limits,
            dt_hours=dt_hours,
        )
        self.scheduled_actions: List[MicrogridAction] = []
        self.is_solved = False

    def solve_episode(
        self,
        realized_trajectories: Dict[str, np.ndarray],
        initial_temp_c: float = 22.0,
        initial_soc: float = 0.50,
    ) -> List[MicrogridAction]:
        """Solves global multi-period LP across T=horizon_steps.
        Variables per step t:
        [Q_cool_t, Q_heat_t, P_c_t, P_d_t, P_imp_t, P_exp_t, s_high_t, s_low_t, T_t+1, E_t+1]
        """
        N = self.horizon_steps
        n_vars_per_step = 10
        total_vars = N * n_vars_per_step

        t_out = realized_trajectories["outdoor_temp_c"]
        solar_irrad = realized_trajectories["solar_irradiance_kw_m2"]
        solar_gen = realized_trajectories["solar_generation_kw"]
        base_demand = realized_trajectories["base_demand_kw"]
        occupancy = realized_trajectories["occupancy"]
        price = realized_trajectories["electricity_price"]
        carbon_intensity = realized_trajectories["carbon_intensity"]

        c = np.zeros(total_vars)
        bounds = []

        # Objective vector c
        for t in range(N):
            base_idx = t * n_vars_per_step
            p_imp_cost = (price[t] + self.weights.lambda_carbon * (carbon_intensity[t] / 1000.0)) * self.dt_hours
            p_exp_rev = (price[t] * self.grid.export_tariff_ratio + self.weights.lambda_carbon * (carbon_intensity[t] / 1000.0)) * self.dt_hours
            p_deg = self.weights.lambda_degradation * self.dt_hours
            p_comfort = self.weights.lambda_comfort * self.dt_hours

            c[base_idx + 0] = 0.0          # Q_cool
            c[base_idx + 1] = 0.0          # Q_heat
            c[base_idx + 2] = p_deg        # P_c
            c[base_idx + 3] = p_deg        # P_d
            c[base_idx + 4] = p_imp_cost   # P_imp
            c[base_idx + 5] = -p_exp_rev   # P_exp
            c[base_idx + 6] = p_comfort    # s_high
            c[base_idx + 7] = p_comfort    # s_low
            c[base_idx + 8] = 0.0          # T_t+1
            c[base_idx + 9] = 0.0          # E_t+1

            # Bounds
            bounds.extend([
                (0.0, self.hvac.cooling_capacity_thermal_kw),
                (0.0, self.hvac.heating_capacity_thermal_kw),
                (0.0, self.battery.max_charge_power_kw),
                (0.0, self.battery.max_discharge_power_kw),
                (0.0, self.grid.max_import_kw),
                (0.0, self.grid.max_export_kw),
                (0.0, None),
                (0.0, None),
                (15.0, 35.0), # T_t+1 physical range
                (self.battery.soc_min * self.battery.capacity_kwh, self.battery.soc_max * self.battery.capacity_kwh),
            ])

        A_eq_list = []
        b_eq_list = []
        A_ub_list = []
        b_ub_list = []

        # Thermal dynamics parameters
        c_th = self.building.c_th_kwh_per_c
        ua = self.building.ua_kw_per_c
        dt = self.dt_hours
        cop_c = self.hvac.cop_cooling
        cop_h = self.hvac.cop_heating
        eta_c = self.battery.charge_efficiency
        eta_d = self.battery.discharge_efficiency

        for t in range(N):
            base_idx = t * n_vars_per_step
            q_int = self.building.internal_gain_base_kw + self.building.internal_gain_occupancy_multiplier * occupancy[t]
            q_sol = self.building.solar_gain_factor * (solar_irrad[t] * 100.0)

            # 1. Power balance equality:
            # (1/cop_c)*Q_cool + (1/cop_h)*Q_heat + P_c - P_d - P_imp + P_exp = P_solar - P_base
            row_p = np.zeros(total_vars)
            row_p[base_idx + 0] = 1.0 / cop_c
            row_p[base_idx + 1] = 1.0 / cop_h
            row_p[base_idx + 2] = 1.0
            row_p[base_idx + 3] = -1.0
            row_p[base_idx + 4] = -1.0
            row_p[base_idx + 5] = 1.0
            A_eq_list.append(row_p)
            b_eq_list.append(solar_gen[t] - base_demand[t])

            # 2. Thermal state transition equality:
            # T_{t+1} - [1 - (dt*UA/c_th)]*T_t + (dt/c_th)*Q_cool - (dt/c_th)*Q_heat = (dt/c_th)*[UA*T_out + Q_int + Q_sol]
            row_t = np.zeros(total_vars)
            row_t[base_idx + 8] = 1.0              # T_{t+1}
            row_t[base_idx + 0] = dt / c_th       # + (dt/c_th)*Q_cool
            row_t[base_idx + 1] = -dt / c_th      # - (dt/c_th)*Q_heat
            decay_factor = 1.0 - (dt * ua / c_th)
            rhs_t = (dt / c_th) * (ua * t_out[t] + q_int + q_sol)

            if t == 0:
                rhs_t += decay_factor * initial_temp_c
            else:
                prev_base = (t - 1) * n_vars_per_step
                row_t[prev_base + 8] = -decay_factor

            A_eq_list.append(row_t)
            b_eq_list.append(rhs_t)

            # 3. Battery state transition equality:
            # E_{t+1} - E_t - eta_c*dt*P_c + (dt/eta_d)*P_d = 0
            row_e = np.zeros(total_vars)
            row_e[base_idx + 9] = 1.0
            row_e[base_idx + 2] = -eta_c * dt
            row_e[base_idx + 3] = dt / eta_d
            rhs_e = 0.0

            if t == 0:
                rhs_e = initial_soc * self.battery.capacity_kwh
            else:
                prev_base = (t - 1) * n_vars_per_step
                row_e[prev_base + 9] = -1.0

            A_eq_list.append(row_e)
            b_eq_list.append(rhs_e)

            # 4. Comfort band inequalities:
            # T_{t+1} - s_high <= T_max  ->  T_{t+1} - s_high <= 24.0
            # -T_{t+1} - s_low <= -T_min ->  -T_{t+1} - s_low <= -21.0
            row_u1 = np.zeros(total_vars)
            row_u1[base_idx + 8] = 1.0
            row_u1[base_idx + 6] = -1.0
            A_ub_list.append(row_u1)
            b_ub_list.append(self.building.temp_max_comfort_c)

            row_u2 = np.zeros(total_vars)
            row_u2[base_idx + 8] = -1.0
            row_u2[base_idx + 7] = -1.0
            A_ub_list.append(row_u2)
            b_ub_list.append(-self.building.temp_min_comfort_c)

        A_eq = np.array(A_eq_list)
        b_eq = np.array(b_eq_list)
        A_ub = np.array(A_ub_list)
        b_ub = np.array(b_ub_list)

        res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

        self.scheduled_actions = []
        if res.success:
            for t in range(N):
                base_idx = t * n_vars_per_step
                action = MicrogridAction(
                    hvac_cooling_thermal_kw=float(res.x[base_idx + 0]),
                    hvac_heating_thermal_kw=float(res.x[base_idx + 1]),
                    battery_charge_kw=float(res.x[base_idx + 2]),
                    battery_discharge_kw=float(res.x[base_idx + 3]),
                    ev_charge_kw=0.0,
                )
                self.scheduled_actions.append(action)
            self.is_solved = True
        else:
            # Fallback zero actions
            for _ in range(N):
                self.scheduled_actions.append(MicrogridAction())

        return self.scheduled_actions

    def get_action_for_step(self, step: int) -> MicrogridAction:
        if 0 <= step < len(self.scheduled_actions):
            return self.scheduled_actions[step]
        return MicrogridAction()
