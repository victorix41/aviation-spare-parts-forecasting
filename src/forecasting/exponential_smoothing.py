"""Simple exponential-smoothing forecasting."""

from __future__ import annotations

import pandas as pd

from src.forecasting.forecast_models import (
    ForecastResult,
)
from src.forecasting.forecast_utils import (
    ForecastingError,
    create_constant_forecast,
    prepare_demand_series,
    validate_forecast_horizon,
)


def forecast_exponential_smoothing(
    demand: pd.Series,
    *,
    forecast_horizon: int,
    smoothing_level: float = 0.30,
) -> ForecastResult:
    """Forecast using simple exponential smoothing."""

    validate_forecast_horizon(
        forecast_horizon
    )

    prepared = prepare_demand_series(
        demand
    )

    if not 0 < smoothing_level <= 1:
        raise ForecastingError(
            "Smoothing level must be greater than zero "
            "and no greater than one."
        )

    level = float(
        prepared.iloc[0]
    )

    fitted_values = [
        level
    ]

    for observation in prepared.iloc[1:]:
        fitted_values.append(
            level
        )

        level = (
            smoothing_level
            * float(observation)
            + (
                1 - smoothing_level
            )
            * level
        )

    return ForecastResult(
        model_name="exponential_smoothing",
        forecast_horizon=forecast_horizon,
        forecast_values=create_constant_forecast(
            level,
            forecast_horizon,
        ),
        fitted_values=pd.Series(
            fitted_values,
            dtype=float,
        ),
        parameters={
            "smoothing_level": smoothing_level,
        },
    )