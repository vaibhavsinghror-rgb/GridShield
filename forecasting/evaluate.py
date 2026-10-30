"""Evaluation metrics for time-series forecasters.
Computes MAE, RMSE, and Normalized RMSE (NRMSE).
"""

from typing import Dict, Any
import numpy as np


def compute_forecast_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Computes standard point-forecast accuracy metrics."""
    error = y_pred - y_true
    mae = float(np.mean(np.abs(error)))
    mse = float(np.mean(error ** 2))
    rmse = float(np.sqrt(mse))

    # Normalized RMSE by true mean
    mean_true = float(np.mean(y_true))
    nrmse = rmse / mean_true if abs(mean_true) > 1e-5 else 0.0

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "nrmse": round(nrmse, 4),
    }
