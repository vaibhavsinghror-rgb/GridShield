"""Feature preprocessing and scaler utilities for time-series forecasting.
Strict chronological fitting to eliminate data leakage.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import json


class TimeSeriesScaler:
    def __init__(self):
        self.mean_: Optional[np.ndarray] = None
        self.scale_: Optional[np.ndarray] = None
        self.feature_names: List[str] = []

    def fit(self, X: np.ndarray, feature_names: List[str]) -> "TimeSeriesScaler":
        """Fits mean and std strictly on training set."""
        self.feature_names = feature_names
        self.mean_ = np.nanmean(X, axis=0)
        self.scale_ = np.nanstd(X, axis=0)
        # Avoid division by zero for constant features
        self.scale_[self.scale_ < 1e-6] = 1.0
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.scale_ is None:
            raise ValueError("Scaler has not been fitted.")
        return (X - self.mean_) / self.scale_

    def inverse_transform_target(self, y: np.ndarray, target_col_idx: int = 0) -> np.ndarray:
        """Inverts transformation for the target column."""
        return y * self.scale_[target_col_idx] + self.mean_[target_col_idx]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean": self.mean_.tolist() if self.mean_ is not None else [],
            "scale": self.scale_.tolist() if self.scale_ is not None else [],
            "feature_names": self.feature_names,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimeSeriesScaler":
        scaler = cls()
        scaler.mean_ = np.array(data["mean"])
        scaler.scale_ = np.array(data["scale"])
        scaler.feature_names = data.get("feature_names", [])
        return scaler
