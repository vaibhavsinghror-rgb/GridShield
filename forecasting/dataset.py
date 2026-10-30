"""Dataset generation and PyTorch Dataset class for multi-step rolling load forecasting.
"""

from typing import Tuple, Dict, Any, List
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from grid_sim.weather import ExogenousProfileGenerator, WeatherGenerator
from grid_sim.solar import SolarPV
from grid_sim.tariffs import ElectricityTariff
from grid_sim.carbon import CarbonIntensityModel


def generate_chronological_timeseries(
    num_days: int = 30,
    timestep_hours: float = 0.25,
    seed: int = 42,
) -> pd.DataFrame:
    """Generates continuous synthetic timeseries data over multiple weeks."""
    rng = np.random.default_rng(seed)
    total_steps = int(num_days * 24.0 / timestep_hours)

    weather = WeatherGenerator(seed=seed)
    solar_pv = SolarPV(installed_capacity_kw=40.0)
    tariff = ElectricityTariff()
    carbon = CarbonIntensityModel()

    records = []
    indoor_temp = 22.0

    for step in range(total_steps):
        time_hours = step * timestep_hours
        hour_of_day = time_hours % 24.0
        day_of_week = int((time_hours / 24.0) % 7)  # 5, 6 are weekend

        # Weather
        t_out, irradiance = weather.get_weather_at_time(time_hours)
        # Add small stochastic weather noise
        t_out += rng.normal(0, 0.5)
        irradiance = max(0.0, irradiance + rng.normal(0, 0.03) if irradiance > 0 else 0.0)

        # Occupancy
        is_weekend = day_of_week in [5, 6]
        if is_weekend:
            occupancy = 5 if 10.0 <= hour_of_day <= 18.0 else 0
        else:
            if 8.0 <= hour_of_day <= 17.0:
                occupancy = 40 + int(rng.integers(-3, 4))
            elif 17.0 < hour_of_day <= 20.0:
                occupancy = 15 + int(rng.integers(-2, 3))
            else:
                occupancy = 2

        # Base building load (uncontrollable)
        base_load_kw = 8.0 + 0.3 * occupancy
        if not is_weekend and 9.0 <= hour_of_day <= 17.0:
            base_load_kw += 5.0
        # Add stochastic load fluctuation
        base_load_kw = max(3.0, base_load_kw + rng.normal(0, 0.8))

        # Approximate indoor drift
        indoor_temp = indoor_temp + 0.05 * (t_out - indoor_temp) + 0.02 * occupancy / 10.0
        indoor_temp = max(19.0, min(26.0, indoor_temp))

        # Solar PV
        solar_gen = solar_pv.generate(irradiance)

        # Tariff & Carbon
        price = tariff.get_rate_at_hour(hour_of_day)
        carbon_int = carbon.get_intensity_at_hour(hour_of_day)

        records.append({
            "step": step,
            "time_hours": time_hours,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "base_demand_kw": base_load_kw,
            "outdoor_temp_c": t_out,
            "indoor_temp_c": indoor_temp,
            "occupancy": occupancy,
            "solar_generation_kw": solar_gen,
            "electricity_price": price,
            "carbon_intensity": carbon_int,
        })

    return pd.DataFrame(records)


class TimeSeriesWindowDataset(Dataset):
    """Creates rolling (lookback -> horizon) window samples for training neural forecasters."""

    def __init__(
        self,
        features: np.ndarray,
        targets: np.ndarray,
        history_steps: int = 96,
        horizon_steps: int = 96,
    ):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.targets = torch.tensor(targets, dtype=torch.float32)
        self.history_steps = history_steps
        self.horizon_steps = horizon_steps
        self.num_samples = len(features) - history_steps - horizon_steps + 1

    def __len__(self) -> int:
        return max(0, self.num_samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self.features[idx : idx + self.history_steps]
        y = self.targets[idx + self.history_steps : idx + self.history_steps + self.horizon_steps]
        return x, y
