"""Shared objective formulations and cost weights for microgrid optimization.
Computes electricity expense, carbon emission penalty, battery degradation, and comfort penalties.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field


class ObjectiveWeights(BaseModel):
    lambda_carbon: float = Field(0.05, description="Weight on carbon emissions ($/kgCO2)")
    lambda_degradation: float = Field(0.015, description="Weight on battery degradation ($/kWh throughput)")
    lambda_comfort: float = Field(2.0, description="Weight on comfort violation ($/°C-hour)")
    lambda_terminal_soc: float = Field(0.10, description="Terminal SoC maintenance weight ($/kWh)")


def compute_objective_components(
    grid_import_kwh: float,
    grid_export_kwh: float,
    electricity_price_per_kwh: float,
    carbon_intensity_gco2: float,
    battery_throughput_kwh: float,
    comfort_violation_deg_hours: float,
    weights: ObjectiveWeights,
    export_tariff_ratio: float = 0.50,
    export_carbon_credit: bool = True,
) -> Dict[str, float]:
    """Computes individual and unified cost metrics."""
    # Electricity monetary cost
    import_cost = grid_import_kwh * electricity_price_per_kwh
    export_revenue = grid_export_kwh * (electricity_price_per_kwh * export_tariff_ratio)
    net_electricity_cost = import_cost - export_revenue

    # Operational carbon emissions
    import_emissions_kg = (carbon_intensity_gco2 * grid_import_kwh) / 1000.0
    export_credit_kg = (
        (carbon_intensity_gco2 * grid_export_kwh) / 1000.0 if export_carbon_credit else 0.0
    )
    net_emissions_kg = import_emissions_kg - export_credit_kg

    # Degradation and comfort
    degradation_cost = battery_throughput_kwh * weights.lambda_degradation
    comfort_penalty = comfort_violation_deg_hours * weights.lambda_comfort
    carbon_penalty = net_emissions_kg * weights.lambda_carbon

    total_objective = net_electricity_cost + carbon_penalty + degradation_cost + comfort_penalty

    return {
        "net_electricity_cost": net_electricity_cost,
        "net_emissions_kg": net_emissions_kg,
        "degradation_cost": degradation_cost,
        "comfort_penalty": comfort_penalty,
        "total_objective": total_objective,
    }
