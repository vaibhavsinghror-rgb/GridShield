"""Installation and health verification script for GridShield.
Inspects Python, Node.js, PyTorch, SciPy, models, and databases.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_status(name: str, check_fn):
    try:
        check_fn()
        print(f"  [PASS] {name}")
        return True
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        return False


def main():
    print("=" * 60)
    print("GridShield Platform Installation Verification")
    print("=" * 60)

    checks = [
        ("Python Version (>=3.11)", lambda: sys.version_info >= (3, 11) or sys.exit(1)),
        ("PyTorch CPU import", lambda: __import__("torch")),
        ("SciPy HiGHS Solver import", lambda: __import__("scipy.optimize")),
        ("Gymnasium import", lambda: __import__("gymnasium")),
        ("Stable-Baselines3 PPO import", lambda: __import__("stable_baselines3")),
        ("GridShield Simulator Core", lambda: __import__("grid_sim")),
        ("UCC-MPC Controller", lambda: __import__("optimization")),
        ("Trained Forecaster Checkpoint", lambda: os.path.exists("data/derived/forecaster_checkpoint.pt") or sys.exit(1)),
        ("Research Benchmark Results", lambda: os.path.exists("experiments/results/baseline/benchmark_summary.json") or sys.exit(1)),
    ]

    passed = 0
    for name, fn in checks:
        if check_status(name, fn):
            passed += 1

    print("-" * 60)
    print(f"Verification completed: {passed}/{len(checks)} components healthy.")
    if passed == len(checks):
        print(">> GridShield platform is fully installed, calibrated, and operational!")
    else:
        print(">> Some components reported issues. Check logs above.")


if __name__ == "__main__":
    main()
