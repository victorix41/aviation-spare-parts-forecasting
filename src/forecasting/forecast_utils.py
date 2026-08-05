"""Common utilities for forecasting models."""

from __future__ import annotations

import numpy as np
import pandas as pd


class ForecastingError(ValueError):
    """Raised when a forecast cannot be generated."""


def prepare_demand_series(
    demand: pd.Series,
) -> pd.Series:
    """
    Convert a demand series into validated non-negative numeric values.

    Missing values are interpreted as zero demand.
    """

    if not isinstance(demand, pd.Series):
        raise ForecastingError(
            "Demand must be provided as a pandas Series."
        )

    if demand.empty:
        raise ForecastingError(
            "Demand series contains no observations."
        )

    output = pd.to_numeric(
        demand,
        errors="coerce",
    ).fillna(0.0)

    if not np.isfinite(output).all():
        raise ForecastingError(
            "Demand series contains non-finite values."
        )

    if output.lt(0).any():
        raise ForecastingError(
            "Demand series cannot contain negative values."
        )

    return output.astype(float).reset_index(drop=True)


def validate_forecast_horizon(
    forecast_horizon: int,
) -> None:
    """Validate the requested forecast horizon."""

    if not isinstance(forecast_horizon, int):
        raise ForecastingError(
            "Forecast horizon must be an integer."
        )

    if forecast_horizon <= 0:
        raise ForecastingError(
            "Forecast horizon must be greater than zero."
        )


def create_constant_forecast(
    value: float,
    forecast_horizon: int,
) -> pd.Series:
    """Create a constant future forecast series."""

    validate_forecast_horizon(
        forecast_horizon
    )

    return pd.Series(
        [max(0.0, float(value))]
        * forecast_horizon,
        dtype=float,
    )