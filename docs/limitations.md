# Limitations and Safety Disclaimers

## 1. Simulation and Decision-Support Disclaimer
GridShield is strictly a research, simulation, and decision-support software platform. It is **not certified or licensed for direct supervisory control of live electrical infrastructure**, grid interconnects, utility switchgear, or commercial building automation systems (BMS). All control setpoints, simulated overrides, and schedules are generated within simulated mathematical environments.

## 2. Modeling Assumptions and Limitations

### 2.1 Single-Zone Thermal Modeling
- The building envelope is modeled as a lumped single-zone Resistance-Capacitance (RC) thermodynamic system.
- Does not model spatial temperature gradients, multi-zone convective airflow, radiant floor heating dynamics, or humidity/latent heat loads.

### 2.2 Battery Degradation Proxy
- Battery degradation is approximated using an empirical linear throughput proxy ($\lambda_D$ per kWh cycled).
- It does not account for complex electrochemical aging mechanisms, including solid electrolyte interphase (SEI) growth, lithium plating, C-rate thermal stress, or depth-of-discharge (DoD) non-linearities.

### 2.3 Linear Optimization Formulation
- The core UCC-MPC optimizer utilizes a linear program solved via HiGHS.
- HVAC COP is modeled as piecewise constant rather than non-linearly dependent on instantaneous lift (ambient vs condensing temperatures).

### 2.4 Audit Log Guarantees
- The audit log is implemented using an application-level append-only schema in SQLite.
- It does not claim tamper-proof cryptographic immutability or distributed ledger consensus.
