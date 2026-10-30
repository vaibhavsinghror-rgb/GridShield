"""Reward calculation for Gymnasium Microgrid RL Environment.
Penalizes electricity costs, carbon emissions, battery throughput degradation, and comfort deviations.
"""

from typing import Dict, Any


class GridShieldRewardCalculator:
    def __init__(
        self,
        lambda_carbon: float = 0.05,
        lambda_degradation: float = 0.015,
        lambda_comfort: float = 2.0,
        reward_scale: float = 0.10,
    ):
        self.lambda_carbon = lambda_carbon
        self.lambda_degradation = lambda_degradation
        self.lambda_comfort = lambda_comfort
        self.reward_scale = reward_scale

    def compute_reward(self, telemetry: Dict[str, Any], dt_hours: float = 0.25) -> float:
        """Negative unified cost scaled for stable RL gradients."""
        elec_cost = telemetry["electricity_cost"]
        carbon_cost = telemetry["operational_emissions_kg"] * self.lambda_carbon
        degrad_cost = telemetry["battery_degradation_cost"]
        comfort_penalty = telemetry["comfort_violation_deg"] * dt_hours * self.lambda_comfort

        total_penalty = elec_cost + carbon_cost + degrad_cost + comfort_penalty
        return -float(total_penalty) * self.reward_scale
