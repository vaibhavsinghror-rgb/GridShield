"""CLI script to train and evaluate the PyTorch Temporal Transformer and Baselines.
Usage:
    python scripts/train_forecaster.py --config configs/forecasting.yaml
"""

import os
import sys

# Ensure repository root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import yaml
from forecasting.train import train_forecaster


def main():
    parser = argparse.ArgumentParser(description="Train GridShield Forecaster")
    parser.add_argument("--config", type=str, default="configs/forecasting.yaml", help="Path to config file")
    parser.add_argument("--num-days", type=int, default=30, help="Days of synthetic training data")
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    print(f"Loading configuration from: {args.config}")
    try:
        with open(args.config, "r") as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: could not read {args.config} ({e}), using defaults")
        cfg = {}

    epochs = cfg.get("training", {}).get("num_epochs", args.epochs)
    lr = cfg.get("training", {}).get("learning_rate", 0.001)

    print("Beginning Forecaster Training Pipeline...")
    metrics = train_forecaster(
        num_days=args.num_days,
        num_epochs=epochs,
        learning_rate=lr,
        seed=args.seed,
    )

    print("\n" + "=" * 60)
    print("FORECASTING BENCHMARK RESULTS (Test Partition)")
    print("=" * 60)
    print(f"{'Model':<25} | {'MAE (kW)':<10} | {'RMSE (kW)':<10} | {'NRMSE':<10}")
    print("-" * 60)
    for model_name, m in metrics.items():
        print(f"{model_name:<25} | {m['mae']:<10.4f} | {m['rmse']:<10.4f} | {m['nrmse']:<10.4f}")
    print("=" * 60)
    print("Forecasting training and evaluation completed successfully!")


if __name__ == "__main__":
    main()
