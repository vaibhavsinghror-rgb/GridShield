"""Classical time-series forecasting baselines:
1. Persistence: repeats last observed value over horizon.
2. Seasonal-Naive: repeats values from the previous 24h cycle (lag 96).
3. Ridge Regression: linear lag-based multi-output baseline.
"""

from typing import Dict, Any, List
import numpy as np
from sklearn.linear_model import Ridge


class PersistenceForecaster:
    def predict(self, history: np.ndarray, horizon_steps: int = 96) -> np.ndarray:
        """Repeats the last observed target value across the entire horizon."""
        last_val = history[-1]
        return np.full(horizon_steps, last_val)


class SeasonalNaiveForecaster:
    def predict(self, history: np.ndarray, horizon_steps: int = 96, season_length: int = 96) -> np.ndarray:
        """Uses the values from the previous diurnal cycle (96 steps ago)."""
        if len(history) < season_length:
            return np.full(horizon_steps, history[-1])
        seasonal_slice = history[-season_length:]
        # Tile if horizon exceeds season length
        repeats = int(np.ceil(horizon_steps / season_length))
        tiled = np.tile(seasonal_slice, repeats)
        return tiled[:horizon_steps]


class RidgeForecaster:
    def __init__(self, alpha: float = 1.0):
        self.model = Ridge(alpha=alpha)
        self.is_fitted = False

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "RidgeForecaster":
        self.model.fit(X, Y)
        self.is_fitted = True
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Model is not fitted.")
        if x.ndim == 1:
            x = x.reshape(1, -1)
        return self.model.predict(x)[0]
