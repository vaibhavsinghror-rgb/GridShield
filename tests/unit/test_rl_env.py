"""Tests for Gymnasium microgrid environment and PPO training pipeline.
Verifies WP7 Gate requirements.
"""

import os
import pytest
import numpy as np
from engagement_env.energy_env import GridShieldEnergyEnv
from agents.ppo_agent import train_ppo, evaluate_ppo


def test_gym_environment_conformance():
    """Verify standard Gymnasium reset, step, shapes, and boundaries."""
    env = GridShieldEnergyEnv(scenario="typical_weekday", seed=42)

    obs, info = env.reset(seed=42)
    assert obs.shape == (10,)
    assert "raw_obs" in info

    # Take a sample action
    action = env.action_space.sample()
    next_obs, reward, terminated, truncated, step_info = env.step(action)

    assert next_obs.shape == (10,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert "telemetry" in step_info
    assert "safety_violations" in step_info


def test_gym_episode_termination():
    """Verify episode terminates precisely after 96 steps."""
    env = GridShieldEnergyEnv(scenario="typical_weekday", seed=42)
    obs, _ = env.reset()

    terminated = False
    step_count = 0
    action = np.array([0.5, 0.0], dtype=np.float32)

    while not terminated:
        obs, reward, terminated, truncated, _ = env.step(action)
        step_count += 1

    assert step_count == 96
    assert terminated is True


def test_ppo_short_train_and_reload():
    """Verify short PPO training run, model serialization, and evaluation."""
    tmp_dir = "experiments/results/test_rl"
    model_path = train_ppo(total_timesteps=512, checkpoint_dir=tmp_dir, seed=42)

    assert os.path.exists(model_path)

    eval_results = evaluate_ppo(model_path, episodes=1, seed=42)
    assert "mean_reward" in eval_results
    assert "mean_electricity_cost_usd" in eval_results
