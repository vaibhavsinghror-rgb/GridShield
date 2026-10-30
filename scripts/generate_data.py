"""Deterministic simulation and synthetic data generation script.
Saves raw and derived dataset manifests to data/raw and data/derived.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
import pandas as pd
from forecasting.dataset import generate_chronological_timeseries


def main():
    parser = argparse.ArgumentParser(description="Generate deterministic GridShield datasets")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--days", type=int, default=60, help="Number of days to generate")
    parser.add_argument("--out-dir", type=str, default="data/raw", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs("data/manifests", exist_ok=True)

    print(f"Generating {args.days} days of deterministic microgrid time series (seed={args.seed})...")
    df = generate_chronological_timeseries(num_days=args.days, seed=args.seed)

    csv_path = os.path.join(args.out_dir, "microgrid_timeseries.csv")
    df.to_csv(csv_path, index=False)
    print(f"Saved {len(df)} records to {csv_path}")

    manifest = {
        "dataset_name": "GridShield Synthetic Multi-Season Microgrid Timeseries",
        "seed": args.seed,
        "days": args.days,
        "records": len(df),
        "timestep_minutes": 15,
        "columns": list(df.columns),
        "summary": {
            "mean_load_kw": float(df["base_demand_kw"].mean()),
            "max_load_kw": float(df["base_demand_kw"].max()),
            "mean_temp_c": float(df["outdoor_temp_c"].mean()),
            "mean_solar_kw": float(df["solar_generation_kw"].mean()),
        }
    }

    manifest_path = "data/manifests/dataset_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Saved dataset manifest to {manifest_path}")


if __name__ == "__main__":
    main()
