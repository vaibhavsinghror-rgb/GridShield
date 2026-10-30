# Literature Review: Carbon-Aware Microgrid Energy Management

## 1. Prior Art and Foundational Work

### 1.1 Model Predictive Control in Building Microgrids
Model Predictive Control (MPC) has emerged as the standard theoretical framework for commercial building energy management and microgrid dispatch.
- **Oldewurtel et al. (2012)** demonstrated stochastic Model Predictive Control for building climate control using weather forecasts, proving that look-ahead scheduling outperforms rule-based hysteresis thermostats by utilizing thermal building capacitance.
- **Parisio et al. (2014)** formulated microgrid energy management as a mixed-integer linear programming (MILP) MPC problem, coordinating distributed generation, battery storage, and controllable loads.

### 1.2 Carbon-Aware Energy Dispatch
Traditional microgrid MPC targets pure monetary cost minimization under time-of-use (TOU) or peak demand tariffs. Recent literature incorporates marginal and average grid carbon emissions:
- **Radovanovic et al. (2022)** examined carbon-aware computing and load shifting across global data centers based on dynamic grid carbon intensities.
- **Stinner et al. (2016)** explored multi-objective optimization balancing operational costs and primary energy emissions in building heat pump and storage systems.

### 1.3 Reinforcement Learning vs. Classical MPC
- **Zhang et al. (2019)** and **Drgona et al. (2020)** surveyed Deep Reinforcement Learning (DRL) for building HVAC control. While model-free algorithms (such as PPO and SAC) adapt without requiring explicit physics identification, they exhibit sample inefficiency, policy instability, and vulnerability to constraint violations during exploration.
- Consequently, hybrid architectures that combine predictive optimization with explicit safety filters have demonstrated superior real-world reliability.

## 2. Distinction of UCC-MPC in GridShield

GridShield's **UCC-MPC** unifies:
1. Multi-step rolling-horizon scheduling over 24 hours.
2. Dual-objective joint minimization of volumetric electricity cost and grid carbon emissions.
3. Explicit physical conservation constraints: Kirchhoff power balance, BESS state of charge, and building envelope thermal dynamics.
4. Risk-sensitive uncertainty handling via empirical Conditional Value-at-Risk (CVaR).
5. A deterministic runtime Action Safety Filter providing hard feasibility guarantees before dispatch execution.

## References
1. F. Oldewurtel, et al., "Use of model predictive control and weather forecasts for energy efficient building climate control," *Energy and Buildings*, vol. 45, pp. 15–27, 2012.
2. A. Parisio, et al., "A Model Predictive Control Approach to Microgrid Operation Optimization," *IEEE Trans. Control Syst. Technol.*, vol. 22, no. 5, pp. 1813–1827, 2014.
3. J. Drgona, et al., "All you need to know about model predictive control for buildings," *Annual Reviews in Control*, vol. 50, pp. 190–232, 2020.
4. A. Radovanovic, et al., "Carbon-aware computing for globally distributed datacenters," *IEEE Micro*, vol. 42, no. 4, pp. 38–47, 2022.
