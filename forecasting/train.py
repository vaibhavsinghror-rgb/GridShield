"""Training pipeline for the Temporal Transformer Forecaster and Baselines.
Saves checkpoint artifacts and produces rigorous benchmark tables.
"""

import os
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import numpy as np

from forecasting.dataset import generate_chronological_timeseries, TimeSeriesWindowDataset
from forecasting.features import TimeSeriesScaler
from forecasting.transformer import TemporalTransformerForecaster
from forecasting.baselines import PersistenceForecaster, SeasonalNaiveForecaster, RidgeForecaster
from forecasting.evaluate import compute_forecast_metrics


def train_forecaster(
    num_days: int = 40,
    history_steps: int = 96,
    horizon_steps: int = 96,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    num_epochs: int = 12,
    output_dir: str = "data/derived",
    seed: int = 42,
) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    torch.manual_seed(seed)
    np.random.seed(seed)

    # 1. Generate full dataset
    df = generate_chronological_timeseries(num_days=num_days, seed=seed)
    feature_cols = [
        "base_demand_kw",
        "outdoor_temp_c",
        "indoor_temp_c",
        "occupancy",
        "solar_generation_kw",
        "electricity_price",
        "carbon_intensity",
    ]
    raw_features = df[feature_cols].values
    raw_targets = df["base_demand_kw"].values

    # 2. Chronological Split (70% train, 15% val, 15% test)
    N = len(df)
    train_end = int(0.70 * N)
    val_end = int(0.85 * N)

    train_raw = raw_features[:train_end]
    val_raw = raw_features[train_end:val_end]
    test_raw = raw_features[val_end:]

    # 3. Fit scaler strictly on training data
    scaler = TimeSeriesScaler()
    scaler.fit(train_raw, feature_cols)

    train_norm = scaler.transform(train_raw)
    val_norm = scaler.transform(val_raw)
    test_norm = scaler.transform(test_raw)

    train_targets_norm = train_norm[:, 0]
    val_targets_norm = val_norm[:, 0]
    test_targets_norm = test_norm[:, 0]

    # Save scaler
    scaler_path = os.path.join(output_dir, "scaler.json")
    with open(scaler_path, "w") as f:
        json.dump(scaler.to_dict(), f, indent=2)

    # 4. PyTorch DataLoaders
    train_dataset = TimeSeriesWindowDataset(train_norm, train_targets_norm, history_steps, horizon_steps)
    val_dataset = TimeSeriesWindowDataset(val_norm, val_targets_norm, history_steps, horizon_steps)
    test_dataset = TimeSeriesWindowDataset(test_norm, test_targets_norm, history_steps, horizon_steps)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # 5. Initialize Model
    model = TemporalTransformerForecaster(
        input_dim=len(feature_cols),
        d_model=64,
        nhead=4,
        num_encoder_layers=2,
        dim_feedforward=128,
        dropout=0.1,
        history_steps=history_steps,
        horizon_steps=horizon_steps,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    criterion = nn.MSELoss()

    best_val_loss = float("inf")
    checkpoint_path = os.path.join(output_dir, "forecaster_checkpoint.pt")

    for epoch in range(num_epochs):
        model.train()
        train_loss = 0.0
        for x, y in train_loader:
            optimizer.zero_grad()
            preds = model(x)
            loss = criterion(preds, y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(x)
        train_loss /= len(train_dataset)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x, y in val_loader:
                preds = model(x)
                loss = criterion(preds, y)
                val_loss += loss.item() * len(x)
        val_loss /= len(val_dataset)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "input_dim": len(feature_cols),
                    "history_steps": history_steps,
                    "horizon_steps": horizon_steps,
                },
                checkpoint_path,
            )

    # 6. Evaluation against Baselines on Test Set
    test_x_list = []
    test_y_list = []
    for i in range(len(test_dataset)):
        x, y = test_dataset[i]
        test_x_list.append(x.numpy())
        test_y_list.append(y.numpy())

    test_x = np.array(test_x_list)
    test_y_norm = np.array(test_y_list)

    # Unscale ground truth
    test_y_real = scaler.inverse_transform_target(test_y_norm, target_col_idx=0)

    # Model predictions
    model.load_state_dict(torch.load(checkpoint_path, weights_only=True)["model_state_dict"])
    model.eval()
    with torch.no_grad():
        transformer_preds_norm = model(torch.tensor(test_x, dtype=torch.float32)).numpy()
    transformer_preds = scaler.inverse_transform_target(transformer_preds_norm, target_col_idx=0)

    # Baselines
    persistence = PersistenceForecaster()
    seasonal_naive = SeasonalNaiveForecaster()

    # Ridge baseline
    ridge = RidgeForecaster()
    ridge_train_x = []
    ridge_train_y = []
    for i in range(len(train_dataset)):
        x, y = train_dataset[i]
        ridge_train_x.append(x.flatten().numpy())
        ridge_train_y.append(y.numpy())
    ridge.fit(np.array(ridge_train_x), np.array(ridge_train_y))

    ridge_preds_norm = np.array([ridge.predict(x.flatten()) for x in test_x])
    ridge_preds = scaler.inverse_transform_target(ridge_preds_norm, target_col_idx=0)

    # Collect persistence and seasonal naive predictions
    pers_preds = np.array([persistence.predict(test_raw[i : i + history_steps, 0], horizon_steps) for i in range(len(test_dataset))])
    sn_preds = np.array([seasonal_naive.predict(test_raw[i : i + history_steps, 0], horizon_steps) for i in range(len(test_dataset))])

    # Compute metrics
    metrics = {
        "persistence": compute_forecast_metrics(test_y_real, pers_preds),
        "seasonal_naive": compute_forecast_metrics(test_y_real, sn_preds),
        "ridge_regression": compute_forecast_metrics(test_y_real, ridge_preds),
        "temporal_transformer": compute_forecast_metrics(test_y_real, transformer_preds),
    }

    # Save metrics report
    report_path = os.path.join(output_dir, "forecast_evaluation.json")
    with open(report_path, "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics
