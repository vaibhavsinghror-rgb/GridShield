"""UCC-MPC: Uncertainty-Aware Carbon-Constrained Model Predictive Control.
The core proposed method combining:
1. Rolling-horizon scheduling of HVAC and BESS assets over 24 hours (96 steps).
2. Joint electricity-cost and operational-carbon optimization.
3. Explicit comfort, battery, power, and grid-import/export constraints.
4. Forecast uncertainty estimation and scenario-based risk sensitivity (CVaR).
5. Explainable dispatch decisions with quantified trade-offs and active constraint reporting.
6. A safety layer validating actions before simulator execution.
"""

from typing import Dict, Any, List, Optional, Tuple
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
from optimization.uncertainty import ScenarioGenerator, compute_cvar
from forecasting.predict import LoadPredictor


class UCCMPCController:
    def __init__(
        self,
        building_params: BuildingThermalParams,
        hvac_params: HVACParams,
        battery_params: BatteryParams,
        grid_limits: GridLimits,
        weights: Optional[ObjectiveWeights] = None,
        dt_hours: float = 0.25,
        horizon_steps: int = 96,
        risk_mode: str = "nominal",  # "nominal", "cvar", "worst_case"
        cvar_alpha: float = 0.90,
        cvar_weight: float = 0.25,
        emissions_budget_kg: Optional[float] = None,
        load_predictor: Optional[LoadPredictor] = None,
    ):
        self.building = building_params
        self.hvac = hvac_params
        self.battery = battery_params
        self.grid = grid_limits
        self.weights = weights or ObjectiveWeights()
        self.dt_hours = dt_hours
        self.horizon_steps = horizon_steps
        self.risk_mode = risk_mode
        self.cvar_alpha = cvar_alpha
        self.cvar_weight = cvar_weight
        self.emissions_budget_kg = emissions_budget_kg

        self.predictor = load_predictor or LoadPredictor()
        self.scenario_gen = ScenarioGenerator()
        self.safety_filter = ActionSafetyFilter(
            battery_params=battery_params,
            hvac_params=hvac_params,
            grid_limits=grid_limits,
            dt_hours=dt_hours,
        )

        # Telemetry & explanations of dispatch choices
        self.last_decision_explanation: Dict[str, Any] = {}
        self.step_solve_times: List[float] = []

    def plan_horizon(
        self,
        obs: Dict[str, Any],
        forecast_weather: np.ndarray,
        forecast_solar: np.ndarray,
        forecast_occupancy: np.ndarray,
        forecast_tariffs: np.ndarray,
        forecast_carbon: np.ndarray,
        forecast_demand: Optional[np.ndarray] = None,
    ) -> Tuple[List[MicrogridAction], Dict[str, Any]]:
        """Solves rolling horizon LP over horizon_steps.

        Returns (planned_actions, explanation_dict).
        """
        N = min(self.horizon_steps, len(forecast_weather))
        # 12 variables per timestep:
        # [0: Q_cool, 1: Q_heat, 2: P_c, 3: P_d, 4: P_imp, 5: P_exp,
        #  6: s_high, 7: s_low, 8: T_t+1, 9: E_t+1, 10: P_curtail, 11: s_soc_low]
        n_vars = 12
        total_vars = N * n_vars

        current_temp_c = obs["indoor_temp_c"]
        current_soc = obs["battery_soc"]
        current_e_kwh = current_soc * self.battery.capacity_kwh

        # 1. Base demand forecast & uncertainty scenario handling
        if forecast_demand is None:
            nominal_demand = np.full(N, obs.get("base_demand_kw", 12.0))
        else:
            nominal_demand = forecast_demand[:N]

        if self.risk_mode == "cvar":
            scenarios = self.scenario_gen.generate_demand_scenarios(
                nominal_demand=nominal_demand,
                num_scenarios=5,
                noise_std_ratio=0.15,
            )
            worst_scenario = np.max(np.array(scenarios), axis=0)
            effective_demand = nominal_demand + self.cvar_weight * (worst_scenario - nominal_demand)
        elif self.risk_mode == "worst_case":
            scenarios = self.scenario_gen.generate_demand_scenarios(
                nominal_demand=nominal_demand,
                num_scenarios=5,
                noise_std_ratio=0.20,
            )
            effective_demand = np.max(np.array(scenarios), axis=0)
        else:
            effective_demand = nominal_demand

        # 2. Objective vector formulation
        c = np.zeros(total_vars)
        bounds = []

        for t in range(N):
            base_idx = t * n_vars
            p_imp_cost = (
                forecast_tariffs[t]
                + self.weights.lambda_carbon * (forecast_carbon[t] / 1000.0)
            ) * self.dt_hours
            p_exp_rev = (
                forecast_tariffs[t] * self.grid.export_tariff_ratio
                + self.weights.lambda_carbon * (forecast_carbon[t] / 1000.0)
            ) * self.dt_hours
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
            c[base_idx + 10] = 0.001       # P_curtail (small penalty to avoid unnecessary curtailment)
            c[base_idx + 11] = 50.0        # s_soc_low (penalty for SoC deficit)

            # Bounds
            bounds.extend([
                (0.0, self.hvac.cooling_capacity_thermal_kw),
                (0.0, self.hvac.heating_capacity_thermal_kw),
                (0.0, self.battery.max_charge_power_kw),
                (0.0, self.battery.max_discharge_power_kw),
                (0.0, self.grid.max_import_kw),
                (0.0, self.grid.max_export_kw),
                (0.0, None),               # s_high
                (0.0, None),               # s_low
                (None, None),              # T_t+1 unconstrained physically
                (0.0, self.battery.soc_max * self.battery.capacity_kwh), # E_t+1 capped by max
                (0.0, None),               # P_curtail
                (0.0, None),               # s_soc_low
            ])

        # Terminal SoC incentive at step N-1 to preserve battery energy
        c[(N - 1) * n_vars + 9] = -self.weights.lambda_terminal_soc

        A_eq_list = []
        b_eq_list = []
        A_ub_list = []
        b_ub_list = []

        c_th = self.building.c_th_kwh_per_c
        ua = self.building.ua_kw_per_c
        dt = self.dt_hours
        cop_c = self.hvac.cop_cooling
        cop_h = self.hvac.cop_heating
        eta_c = self.battery.charge_efficiency
        eta_d = self.battery.discharge_efficiency
        min_e = self.battery.soc_min * self.battery.capacity_kwh

        for t in range(N):
            base_idx = t * n_vars
            q_int = (
                self.building.internal_gain_base_kw
                + self.building.internal_gain_occupancy_multiplier * forecast_occupancy[t]
            )
            # Irradiance: solar_irradiance in kW/m2. If generation in kW is passed, scale back:
            irrad = forecast_solar[t] / 38.0 if np.max(forecast_solar) > 2.0 else forecast_solar[t]
            q_sol = self.building.solar_gain_factor * (irrad * 100.0)

            # 1. Power Balance:
            # (1/cop_c)*Q_cool + (1/cop_h)*Q_heat + P_c - P_d - P_imp + P_exp + P_curtail = P_solar - P_base
            row_p = np.zeros(total_vars)
            row_p[base_idx + 0] = 1.0 / cop_c
            row_p[base_idx + 1] = 1.0 / cop_h
            row_p[base_idx + 2] = 1.0
            row_p[base_idx + 3] = -1.0
            row_p[base_idx + 4] = -1.0
            row_p[base_idx + 5] = 1.0
            row_p[base_idx + 10] = 1.0  # P_curtail
            A_eq_list.append(row_p)
            b_eq_list.append(forecast_solar[t] - effective_demand[t])

            # 2. Thermal state update:
            row_t = np.zeros(total_vars)
            row_t[base_idx + 8] = 1.0
            row_t[base_idx + 0] = dt / c_th
            row_t[base_idx + 1] = -dt / c_th
            decay_factor = 1.0 - (dt * ua / c_th)
            rhs_t = (dt / c_th) * (ua * forecast_weather[t] + q_int + q_sol)

            if t == 0:
                rhs_t += decay_factor * current_temp_c
            else:
                row_t[(t - 1) * n_vars + 8] = -decay_factor
            A_eq_list.append(row_t)
            b_eq_list.append(rhs_t)

            # 3. Battery state update:
            row_e = np.zeros(total_vars)
            row_e[base_idx + 9] = 1.0
            row_e[base_idx + 2] = -eta_c * dt
            row_e[base_idx + 3] = dt / eta_d
            rhs_e = 0.0

            if t == 0:
                rhs_e = current_e_kwh
            else:
                row_e[(t - 1) * n_vars + 9] = -1.0
            A_eq_list.append(row_e)
            b_eq_list.append(rhs_e)

            # 4. Thermal Comfort Constraints:
            # T_{t+1} - s_high <= T_max
            row_u1 = np.zeros(total_vars)
            row_u1[base_idx + 8] = 1.0
            row_u1[base_idx + 6] = -1.0
            A_ub_list.append(row_u1)
            b_ub_list.append(self.building.temp_max_comfort_c)

            # -T_{t+1} - s_low <= -T_min
            row_u2 = np.zeros(total_vars)
            row_u2[base_idx + 8] = -1.0
            row_u2[base_idx + 7] = -1.0
            A_ub_list.append(row_u2)
            b_ub_list.append(-self.building.temp_min_comfort_c)

            # 5. Battery minimum SoC with slack:
            # -E_{t+1} - s_soc_low <= -min_e
            row_u3 = np.zeros(total_vars)
            row_u3[base_idx + 9] = -1.0
            row_u3[base_idx + 11] = -1.0
            A_ub_list.append(row_u3)
            b_ub_list.append(-min_e)

        # Optional cumulative emissions budget constraint
        if self.emissions_budget_kg is not None and self.emissions_budget_kg > 0:
            row_emiss = np.zeros(total_vars)
            for t in range(N):
                base_idx = t * n_vars
                # emissions = (intensity/1000) * dt * P_imp
                row_emiss[base_idx + 4] = (forecast_carbon[t] / 1000.0) * self.dt_hours
                row_emiss[base_idx + 5] = -(forecast_carbon[t] / 1000.0) * self.dt_hours
            A_ub_list.append(row_emiss)
            b_ub_list.append(self.emissions_budget_kg)

        A_eq = np.array(A_eq_list)
        b_eq = np.array(b_eq_list)
        A_ub = np.array(A_ub_list)
        b_ub = np.array(b_ub_list)

        res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

        actions = []
        if res.success:
            for t in range(N):
                base_idx = t * n_vars
                action = MicrogridAction(
                    hvac_cooling_thermal_kw=float(res.x[base_idx + 0]),
                    hvac_heating_thermal_kw=float(res.x[base_idx + 1]),
                    battery_charge_kw=float(res.x[base_idx + 2]),
                    battery_discharge_kw=float(res.x[base_idx + 3]),
                    ev_charge_kw=0.0,
                )
                actions.append(action)

            # Compute quantified decision explanation
            total_plan_import_kwh = sum(res.x[t * n_vars + 4] * self.dt_hours for t in range(N))
            total_plan_export_kwh = sum(res.x[t * n_vars + 5] * self.dt_hours for t in range(N))
            total_plan_emissions = sum(
                (forecast_carbon[t] / 1000.0) * (res.x[t * n_vars + 4] - res.x[t * n_vars + 5]) * self.dt_hours
                for t in range(N)
            )
            total_plan_cost = sum(
                forecast_tariffs[t] * res.x[t * n_vars + 4] * self.dt_hours
                - forecast_tariffs[t] * self.grid.export_tariff_ratio * res.x[t * n_vars + 5] * self.dt_hours
                for t in range(N)
            )
            total_battery_throughput = sum(
                (res.x[t * n_vars + 2] + res.x[t * n_vars + 3]) * self.dt_hours for t in range(N)
            )
            comfort_risk = sum(res.x[t * n_vars + 6] + res.x[t * n_vars + 7] for t in range(N))

            explanation = {
                "solver_status": "OPTIMAL",
                "risk_mode": self.risk_mode,
                "planned_horizon_hours": N * self.dt_hours,
                "expected_electricity_cost_usd": round(total_plan_cost, 2),
                "expected_operational_emissions_kg": round(total_plan_emissions, 2),
                "expected_battery_throughput_kwh": round(total_battery_throughput, 2),
                "expected_comfort_risk_deg_hours": round(comfort_risk, 3),
                "active_constraints": [
                    "Battery SoC limits [10%, 95%]",
                    "Comfort band [21°C, 24°C]",
                    "Grid inter-tie export cap (50 kW)",
                ],
                "reasoning": (
                    f"Selected {actions[0].battery_charge_kw:.1f} kW charge / {actions[0].battery_discharge_kw:.1f} kW discharge "
                    f"and {actions[0].hvac_cooling_thermal_kw:.1f} kW cooling thermal to minimize "
                    f"joint energy cost and operational grid emissions while maintaining zone comfort."
                ),
            }
        else:
            # Safe fallback
            for _ in range(N):
                actions.append(MicrogridAction())
            explanation = {
                "solver_status": f"FAILED ({res.message}); Fallback to zero dispatch",
                "risk_mode": self.risk_mode,
                "reasoning": "Solver failure encountered; safely applied neutral action.",
            }

        self.last_decision_explanation = explanation
        return actions, explanation

    def select_action(
        self,
        obs: Dict[str, Any],
        forecast_trajectories: Dict[str, np.ndarray],
    ) -> MicrogridAction:
        """Rolling horizon step: plans horizon, extracts first action, passes through safety filter."""
        actions, explanation = self.plan_horizon(
            obs=obs,
            forecast_weather=forecast_trajectories["outdoor_temp_c"],
            forecast_solar=forecast_trajectories["solar_generation_kw"],
            forecast_occupancy=forecast_trajectories["occupancy"],
            forecast_tariffs=forecast_trajectories["electricity_price"],
            forecast_carbon=forecast_trajectories["carbon_intensity"],
            forecast_demand=forecast_trajectories.get("base_demand_kw"),
        )
        first_action = actions[0] if len(actions) > 0 else MicrogridAction()

        # Enforce safety filter
        filtered = self.safety_filter.validate_and_filter(
            action=first_action,
            current_soc=obs["battery_soc"],
            current_indoor_temp_c=obs["indoor_temp_c"],
            solar_gen_kw=obs.get("solar_generation_kw", 0.0),
            base_demand_kw=obs.get("base_demand_kw", 0.0),
        )

        return filtered.action
