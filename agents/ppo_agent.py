"""PPO Reinforcement Learning Agent for GridShield Microgrid Control.
Uses Stable-Baselines3 PPO with reproducible seeds, checkpoint saving, and evaluation.
"""

import os
import argparse
import yaml
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback

from engagement_env.energy_env import GridShieldEnergyEnv


def train_ppo(
    total_timesteps: int = 5000,
    learning_rate: float = 0.0003,
    checkpoint_dir: str = "experiments/results/rl_checkpoints",
    seed: int = 42,
) -> str:
    """Trains PPO agent on GridShield Gymnasium environment."""
    os.makedirs(checkpoint_dir, exist_ok=True)

    env = GridShieldEnergyEnv(scenario="typical_weekday", seed=seed)

    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=128,
        batch_size=32,
        gamma=0.99,
        seed=seed,
        verbose=1,
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=1000,
        save_path=checkpoint_dir,
        name_prefix="ppo_gridshield",
    )

    print(f"Training PPO policy for {total_timesteps} timesteps...")
    model.learn(total_timesteps=total_timesteps, callback=checkpoint_callback)

    final_model_path = os.path.join(checkpoint_dir, "ppo_final_model.zip")
    model.save(final_model_path)
    print(f"PPO training finished. Model saved to {final_model_path}")
    return final_model_path


def evaluate_ppo(
    model_path: str,
    episodes: int = 3,
    scenario: str = "typical_weekday",
    seed: int = 101,
) -> dict:
    """Evaluates trained PPO model across episodes."""
    env = GridShieldEnergyEnv(scenario=scenario, seed=seed)
    model = PPO.load(model_path, env=env)

    total_rewards = []
    total_costs = []
    total_emissions = []

    for ep in range(episodes):
        obs, _ = env.reset(seed=seed + ep)
        done = False
        ep_reward = 0.0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            done = terminated or truncated

        hist = env.sim.history
        ep_cost = sum(t.electricity_cost for t in hist)
        ep_emiss = sum(t.operational_emissions_kg for t in hist)
        total_rewards.append(ep_reward)
        total_costs.append(ep_cost)
        total_emissions.append(ep_emiss)

    return {
        "mean_reward": float(np.mean(total_rewards)),
        "mean_electricity_cost_usd": float(np.mean(total_costs)),
        "mean_emissions_kg": float(np.mean(total_emissions)),
    }


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate GridShield PPO agent")
    parser.add_argument("--config", type=str, default="configs/rl_energy.yaml", help="Config file")
    parser.add_argument("--timesteps", type=int, default=3000, help="Timesteps to train")
    parser.add_argument("--seed", type=int, default=42, help="Seed")
    args = parser.parse_args()

    saved_path = train_ppo(total_timesteps=args.timesteps, seed=args.seed)
    results = evaluate_ppo(saved_path, episodes=2, seed=args.seed + 10)
    print("\n--- PPO Evaluation Summary ---")
    for k, v in results.items():
        print(f"  {k}: {v:.2f}")


if __name__ == "__main__":
    main()
