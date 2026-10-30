"""Uncertainty Modeling and Scenario Generation for UCC-MPC.
Implements risk-sensitive metrics: Expected Cost, Value-at-Risk (VaR),
and Conditional Value-at-Risk (CVaR).
"""

from typing import List, Dict, Any, Tuple
import numpy as np


class ScenarioGenerator:
    """Generates plausible realization trajectories given nominal forecasts and uncertainty bounds."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def generate_demand_scenarios(
        self,
        nominal_demand: np.ndarray,
        num_scenarios: int = 4,
        noise_std_ratio: float = 0.15,
        bias_ratio: float = 0.0,
    ) -> List[np.ndarray]:
        """Generates K scenarios with auto-correlated disturbance and optional bias."""
        H = len(nominal_demand)
        scenarios = []

        # Scenario 0 is always the nominal trajectory (with bias if testing bias)
        scenarios.append(np.maximum(1.0, nominal_demand * (1.0 + bias_ratio)))

        for _ in range(num_scenarios - 1):
            # Horizon-dependent dispersion
            dispersion = 1.0 + np.linspace(0.0, 0.4, H)
            raw_noise = self.rng.normal(0, noise_std_ratio, H) * dispersion
            # Smooth autoregressive filter
            smooth_noise = np.convolve(raw_noise, np.ones(3) / 3.0, mode="same")
            scen = nominal_demand * (1.0 + bias_ratio + smooth_noise)
            scenarios.append(np.maximum(1.0, scen))

        return scenarios


def compute_cvar(
    scenario_costs: np.ndarray,
    alpha: float = 0.90,
) -> Tuple[float, float]:
    """Computes empirical VaR_alpha and CVaR_alpha from scenario evaluation costs.
    VaR_alpha: alpha-quantile of loss distribution.
    CVaR_alpha: expected loss in the worst (1 - alpha) fraction of scenarios.
    """
    sorted_costs = np.sort(scenario_costs)
    K = len(sorted_costs)
    if K == 0:
        return 0.0, 0.0

    idx = int(np.ceil(alpha * K)) - 1
    idx = max(0, min(K - 1, idx))
    var = float(sorted_costs[idx])

    tail = sorted_costs[idx:]
    cvar = float(np.mean(tail)) if len(tail) > 0 else var

    return var, cvar
