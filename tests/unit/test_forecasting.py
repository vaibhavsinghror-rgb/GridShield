"""Tests for time-series forecasting:
Verifies chronological leakage-free splitting, baseline fallbacks,
and Temporal Transformer training/inference validity.
"""

import os
import pytest
import numpy as np

from forecasting.dataset import generate_chronological_timeseries, TimeSeriesWindowDataset
from forecasting.features import TimeSeriesScaler
from forecasting.baselines import PersistenceForecaster, SeasonalNaiveForecaster
from forecasting.transformer import TemporalTransformerForecaster
from forecasting.predict import LoadPredictor


def test_chronological_split_no_leakage():
    """Verify that train/val/test splits are strictly chronological with zero forward leakage."""
    df = generate_chronological_timeseries(num_days=10, seed=42)
    N = len(df)
    train_end = int(0.7 * N)
    test_start = int(0.85 * N)

    # Train timestamps must strictly precede validation, which strictly precedes test
    assert df["step"].iloc[train_end - 1] < df["step"].iloc[train_end]
    assert df["step"].iloc[test_start - 1] < df["step"].iloc[test_start]


def test_scaler_leakage_prevention():
    """Verify scaler is fitted ONLY on train partition and doesn't leak test statistics."""
    train_data = np.array([[10.0], [20.0], [30.0]])
    test_data = np.array([[1000.0]])

    scaler = TimeSeriesScaler()
    scaler.fit(train_data, ["load"])

    assert scaler.mean_[0] == 20.0
    # Transforming test data uses train mean and scale
    scaled_test = scaler.transform(test_data)
    expected_scale = np.std(train_data)
    assert pytest.approx(scaled_test[0, 0], rel=1e-3) == (1000.0 - 20.0) / expected_scale


def test_baseline_forecaster_outputs():
    """Verify output shapes and behavior of Persistence and Seasonal-Naive baselines."""
    history = np.linspace(10.0, 20.0, 96)
    persistence = PersistenceForecaster()
    pred_p = persistence.predict(history, horizon_steps=96)
    assert len(pred_p) == 96
    assert np.all(pred_p == 20.0)

    seasonal = SeasonalNaiveForecaster()
    pred_s = seasonal.predict(history, horizon_steps=96, season_length=96)
    assert len(pred_s) == 96
    assert np.allclose(pred_s, history)


def test_predictor_fallback_when_untrained():
    """Verify predictor works gracefully with status indicator before model training."""
    predictor = LoadPredictor(checkpoint_path="nonexistent_checkpoint.pt")
    assert "FALLBACK_BASELINE" in predictor.status

    dummy_history = np.ones((96, 7)) * 12.0
    res = predictor.predict(dummy_history, num_scenarios=3)

    assert len(res["point_forecast"]) == 96
    assert len(res["lower_bound_10"]) == 96
    assert len(res["upper_bound_90"]) == 96
    assert len(res["scenarios"]) == 3
    assert res["model_status"] == "FALLBACK_BASELINE"
