"""Gymnasium Microgrid Energy Management Environment.
Conforms strictly to Farama Gymnasium API (reset, step, action_space, observation_space).
Enforces physical safety constraints via the ActionSafetyFilter.
"""

from typing import Tuple, Dict, Any, Optional
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from grid_sim.schemas import MicrogridAction
from grid_sim.microgrid import MicrogridSimulator
from optimization.safety_filter import ActionSafetyFilter
from engagement_env.reward import GridShieldRewardCalculator


class GridShieldEnergyEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        scenario: str = "typical_weekday",
        seed: int = 42,
        max_steps: int = 96,
        dt_hours: float = 0.25,
        normalize_obs: bool = True,
    ):
        super().__init__()
        self.scenario = scenario
        self.default_seed = seed
        self.max_steps = max_steps
        self.dt_hours = dt_hours
        self.normalize_obs = normalize_obs

        self.sim = MicrogridSimulator(scenario=scenario, seed=seed, dt_hours=dt_hours)
        self.safety_filter = ActionSafetyFilter(
            battery_params=self.sim.battery_params,
            hvac_params=self.sim.hvac_params,
            grid_limits=self.sim.grid_limits,
            dt_hours=dt_hours,
        )
        self.reward_calculator = GridShieldRewardCalculator()

        # Action Space:
        # action[0]: HVAC cooling [0.0, 1.0] (mapped to [0, max_cooling_thermal_kw])
        # action[1]: Battery dispatch [-1.0, 1.0] (>0 charge, <0 discharge)
        self.action_space = spaces.Box(
            low=np.array([0.0, -1.0], dtype=np.float32),
            high=np.array([1.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )

        # Observation Space:
        # 10 normalized features:
        # [sin_hour, cos_hour, indoor_temp, outdoor_temp, soc, solar_gen,
        #  base_demand, electricity_price, carbon_intensity, occupancy]
        self.observation_space = spaces.Box(
            low=-np.ones(10, dtype=np.float32) * 5.0,
            high=np.ones(10, dtype=np.float32) * 5.0,
            dtype=np.float32,
        )

        self.current_step = 0

    def _get_obs(self, obs_dict: Dict[str, Any]) -> np.ndarray:
        hour = obs_dict["hour_of_day"]
        sin_hour = np.sin(2.0 * np.pi * hour / 24.0)
        cos_hour = np.cos(2.0 * np.pi * hour / 24.0)

        t_in = (obs_dict["indoor_temp_c"] - 22.5) / 5.0
        t_out = (obs_dict["outdoor_temp_c"] - 25.0) / 15.0
        soc = (obs_dict["battery_soc"] - 0.5) / 0.5
        solar = obs_dict["solar_generation_kw"] / 40.0
        load = (obs_dict["base_demand_kw"] - 15.0) / 15.0
        price = (obs_dict["electricity_price"] - 0.15) / 0.15
        carbon = (obs_dict["carbon_intensity"] - 250.0) / 200.0
        occ = obs_dict["occupancy"] / 50.0

        return np.array(
            [sin_hour, cos_hour, t_in, t_out, soc, solar, load, price, carbon, occ],
            dtype=np.float32,
        )

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        effective_seed = seed if seed is not None else self.default_seed
        self.current_step = 0

        obs_dict = self.sim.reset(initial_temp_c=22.5, initial_soc=0.50)
        return self._get_obs(obs_dict), {"raw_obs": obs_dict}

    def step(
        self, action: np.ndarray
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        # Map normalized actions to physical units
        cool_norm = float(np.clip(action[0], 0.0, 1.0))
        bat_norm = float(np.clip(action[1], -1.0, 1.0))

        cooling_kw = cool_norm * self.sim.hvac_params.cooling_capacity_thermal_kw
        if bat_norm >= 0:
            charge_kw = bat_norm * self.sim.battery_params.max_charge_power_kw
            discharge_kw = 0.0
        else:
            charge_kw = 0.0
            discharge_kw = (-bat_norm) * self.sim.battery_params.max_discharge_power_kw

        raw_action = MicrogridAction(
            hvac_cooling_thermal_kw=cooling_kw,
            hvac_heating_thermal_kw=0.0,
            battery_charge_kw=charge_kw,
            battery_discharge_kw=discharge_kw,
            ev_charge_kw=0.0,
        )

        # Enforce safety filter
        filtered = self.safety_filter.validate_and_filter(
            action=raw_action,
            current_soc=self.sim.battery.soc,
            current_indoor_temp_c=self.sim.building.current_temp_c,
            solar_gen_kw=self.sim.solar.installed_capacity_kw,
            base_demand_kw=10.0,
        )

        telemetry = self.sim.step(filtered.action)
        self.current_step += 1

        reward = self.reward_calculator.compute_reward(telemetry.model_dump(), dt_hours=self.dt_hours)
        terminated = self.current_step >= self.max_steps
        truncated = False

        next_obs_dict = self.sim.get_current_observation()
        obs = self._get_obs(next_obs_dict)

        info = {
            "telemetry": telemetry.model_dump(),
            "safety_violations": len(filtered.violations),
        }

        return obs, reward, terminated, truncated, info
