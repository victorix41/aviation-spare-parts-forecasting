"""Naïve demand forecasting."""

from __future__ import annotations

import pandas as pd

from src.forecasting.forecast_models import (
    ForecastResult,
)
from src.forecasting.forecast_utils import (
    create_constant_forecast,
    prepare_demand_series,
    validate_forecast_horizon,
)


def forecast_naive(
    demand: pd.Series,
    *,
    forecast_horizon: int,
) -> ForecastResult:
    """
    Forecast future demand using the latest observed value.

    This model provides a basic benchmark for model comparison.
    """

    validate_forecast_horizon(
        forecast_horizon
    )

    prepared = prepare_demand_series(
        demand
    )

    latest_value = float(
        prepared.iloc[-1]
    )

    fitted = prepared.shift(1).fillna(
        prepared.iloc[0]
    )

    return ForecastResult(
        model_name="naive",
        forecast_horizon=forecast_horizon,
        forecast_values=create_constant_forecast(
            latest_value,
            forecast_horizon,
        ),
        fitted_values=fitted.astype(float),
        parameters={},
    )