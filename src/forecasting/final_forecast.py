"""Generate final future forecasts using selected models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from src.forecasting.model_registry import (
    run_registered_model,
)


@dataclass(frozen=True)
class FinalPartForecast:
    """Final future forecast for one spare part."""

    part_number: str
    description: str
    demand_pattern: str
    selected_model: str
    forecast_confidence: str
    forecast_horizon_months: int
    monthly_forecast: float
    forecast_3m: float
    forecast_6m: float
    forecast_12m: float
    forecast_values: list[float]
    model_parameters: dict[str, Any]
    advisory_status: str

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable result."""

        return asdict(self)


def generate_final_forecast(
    *,
    part_number: str,
    description: str,
    demand_pattern: str,
    selected_model: str,
    forecast_confidence: str,
    demand: pd.Series,
    forecast_horizon: int,
    model_parameters: dict[str, Any],
) -> FinalPartForecast:
    """Run the selected model against the full demand history."""

    result = run_registered_model(
        model_name=selected_model,
        demand=demand,
        forecast_horizon=forecast_horizon,
        model_parameters=model_parameters,
    )

    values = [
        max(0.0, float(value))
        for value in result.forecast_values
    ]

    forecast_3m = sum(
        values[: min(3, len(values))]
    )

    forecast_6m = sum(
        values[: min(6, len(values))]
    )

    forecast_12m = sum(
        values[: min(12, len(values))]
    )

    monthly_forecast = (
        float(values[0])
        if values
        else 0.0
    )

    return FinalPartForecast(
        part_number=part_number,
        description=description,
        demand_pattern=demand_pattern,
        selected_model=selected_model,
        forecast_confidence=forecast_confidence,
        forecast_horizon_months=forecast_horizon,
        monthly_forecast=monthly_forecast,
        forecast_3m=float(forecast_3m),
        forecast_6m=float(forecast_6m),
        forecast_12m=float(forecast_12m),
        forecast_values=values,
        model_parameters=model_parameters,
        advisory_status=(
            "Decision support only — human review required"
        ),
    )