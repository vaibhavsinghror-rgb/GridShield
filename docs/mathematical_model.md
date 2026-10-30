# GridShield Mathematical and Physical Formulation

## 1. Thermodynamic Building Model

The building thermal zone is formulated as a single-zone Resistance-Capacitance (RC) network:

$$\frac{dT(t)}{dt} = \frac{1}{C_{th}} \left[ UA \cdot (T_o(t) - T(t)) + Q_{int}(t) + Q_{solar}(t) - Q_{cool}(t) + Q_{heat}(t) \right]$$

Discretized using forward Euler with timestep $\Delta t = 0.25$ hours (15 minutes):

$$T_{t+1} = T_t + \frac{\Delta t}{C_{th}} \left[ UA \cdot (T_{o,t} - T_t) + Q_{int,t} + Q_{solar,t} - Q_{cool,t} + Q_{heat,t} \right]$$

where:
- $T_t$: Indoor zone temperature (°C)
- $T_{o,t}$: Ambient outdoor temperature (°C)
- $C_{th}$: Effective thermal capacitance (kWh/°C, default: 15.0)
- $UA$: Overall heat loss coefficient (kW/°C, default: 1.2)
- $Q_{int,t} = Q_{\mathrm{base}} + q_{\mathrm{occ}} \cdot N_{\mathrm{occ},t}$: Internal heat gain from base equipment and occupants (kW)
- $Q_{solar,t} = \gamma_{\mathrm{sol}} \cdot (G_t \cdot 100)$: Solar thermal gain from irradiance $G_t$ in kW/m²
- $Q_{cool,t}, Q_{heat,t}$: Thermal cooling and heating power delivered by HVAC (kW)

HVAC electrical power draw is derived via explicit Coefficient of Performance (COP):

$$P_{\mathrm{HVAC},t} = \frac{Q_{cool,t}}{\mathrm{COP}_{cool}} + \frac{Q_{heat,t}}{\mathrm{COP}_{heat}}$$

## 2. Battery Energy Storage System (BESS) Dynamics

Stored energy evolution $E_t$ (kWh):

$$E_{t+1} = E_t + \eta_c P_{c,t} \Delta t - \frac{P_{d,t} \Delta t}{\eta_d}$$

Subject to physical constraints:

$$E_{\min} \le E_t \le E_{\max}, \quad \forall t$$
$$0 \le P_{c,t} \le P_{c,\max}, \quad 0 \le P_{d,t} \le P_{d,\max}$$
$$P_{c,t} \cdot P_{d,t} = 0 \quad (\text{Mutual Exclusion})$$

Throughput-based degradation proxy:

$$D_t = \lambda_D \cdot (P_{c,t} + P_{d,t}) \Delta t$$

## 3. Microgrid Power Balance

Kirchhoff active power balance at the grid point of common coupling (PCC):

$$P_{\mathrm{grid},t} = P_{\mathrm{base},t} + P_{\mathrm{HVAC},t} + P_{c,t} + P_{\mathrm{EV},t} - P_{d,t} - P_{\mathrm{solar},t}$$

Grid import/export limits:

$$-P_{\mathrm{export},\max} \le P_{\mathrm{grid},t} \le P_{\mathrm{import},\max}$$

Split into unidirectional positive components:

$$P_{\mathrm{grid},t} = P_{\mathrm{grid},t}^{\mathrm{imp}} - P_{\mathrm{grid},t}^{\mathrm{exp}}, \quad P_{\mathrm{grid},t}^{\mathrm{imp}} \ge 0, \quad P_{\mathrm{grid},t}^{\mathrm{exp}} \ge 0$$

## 4. Multi-Objective UCC-MPC Formulation

At each timestep $t$ over a rolling horizon $H = 96$ steps:

$$\min_{Q, P_c, P_d, P^{\mathrm{imp}}, P^{\mathrm{exp}}, s} \sum_{h=0}^{H-1} \Delta t \left[ \pi_{t+h} P_{\mathrm{grid},t+h}^{\mathrm{imp}} - \pi_{t+h} \rho_{\mathrm{exp}} P_{\mathrm{grid},t+h}^{\mathrm{exp}} + \lambda_C \frac{I_{t+h}}{1000} (P_{\mathrm{grid},t+h}^{\mathrm{imp}} - P_{\mathrm{grid},t+h}^{\mathrm{exp}}) + \lambda_D (P_{c,t+h} + P_{d,t+h}) + \lambda_T (s_{high,t+h} + s_{low,t+h}) \right] - \lambda_{soc} E_{t+H}$$

Subject to:
1. Power balance equality $\forall h \in [0, H-1]$
2. Discrete building thermal state transitions $\forall h$
3. Discrete BESS state of charge transitions $\forall h$
4. Thermal comfort slack inequalities:
   $$T_{t+h+1} - s_{high,t+h} \le T_{\max}$$
   $$-T_{t+h+1} - s_{low,t+h} \le -T_{\min}$$
5. Actuator physical bounds: $0 \le Q_{cool} \le Q_{cool,\max}$, $0 \le P_c \le P_{c,\max}$, $0 \le P_d \le P_{d,\max}$
6. Non-negativity: $s_{high}, s_{low}, P^{\mathrm{imp}}, P^{\mathrm{exp}} \ge 0$.

## 5. Conditional Value-at-Risk (CVaR) Formulation

For scenario-based stress testing, given $K$ sampled demand trajectories $\{s_1, \dots, s_K\}$:

$$\text{CVaR}_\alpha(L) = \min_{\gamma} \left\{ \gamma + \frac{1}{K(1 - \alpha)} \sum_{k=1}^K [L(s_k) - \gamma]^+ \right\}$$
