"""Typed models for spare-parts forecasts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ForecastResult:
    """Output produced by one forecasting model."""

    model_name: str
    forecast_horizon: int
    forecast_values: pd.Series
    fitted_values: pd.Series | None
    parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return serialisable forecast metadata."""

        return {
            "model_name": self.model_name,
            "forecast_horizon": self.forecast_horizon,
            "forecast_values": [
                float(value)
                for value in self.forecast_values
            ],
            "fitted_values": (
                [
                    float(value)
                    for value in self.fitted_values
                ]
                if self.fitted_values is not None
                else None
            ),
            "parameters": self.parameters,
        }


@dataclass(frozen=True)
class PartForecast:
    """Forecast output for one spare part."""

    part_number: str
    description: str
    demand_pattern: str
    forecast_eligible: bool
    forecasts: dict[str, ForecastResult]

    def to_dict(self) -> dict[str, Any]:
        """Return serialisable part forecast information."""

        return {
            "part_number": self.part_number,
            "description": self.description,
            "demand_pattern": self.demand_pattern,
            "forecast_eligible": self.forecast_eligible,
            "forecasts": {
                model_name: result.to_dict()
                for model_name, result
                in self.forecasts.items()
            },
        }