"""Moving-average forecasting models."""

from __future__ import annotations

import numpy as np
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


def forecast_moving_average(
    demand: pd.Series,
    *,
    forecast_horizon: int,
    window: int = 3,
) -> ForecastResult:
    """Forecast using the mean of the latest observations."""

    validate_forecast_horizon(
        forecast_horizon
    )

    prepared = prepare_demand_series(
        demand
    )

    if window <= 0:
        raise ForecastingError(
            "Moving-average window must be greater than zero."
        )

    if len(prepared) < window:
        raise ForecastingError(
            "Demand history is shorter than the "
            f"moving-average window of {window}."
        )

    forecast_value = float(
        prepared.iloc[-window:].mean()
    )

    fitted = (
        prepared.shift(1)
        .rolling(
            window=window,
            min_periods=1,
        )
        .mean()
        .fillna(prepared.iloc[0])
    )

    return ForecastResult(
        model_name="moving_average",
        forecast_horizon=forecast_horizon,
        forecast_values=create_constant_forecast(
            forecast_value,
            forecast_horizon,
        ),
        fitted_values=fitted.astype(float),
        parameters={
            "window": window,
        },
    )


def forecast_weighted_moving_average(
    demand: pd.Series,
    *,
    forecast_horizon: int,
    weights: list[float],
) -> ForecastResult:
    """Forecast using weighted recent observations."""

    validate_forecast_horizon(
        forecast_horizon
    )

    prepared = prepare_demand_series(
        demand
    )

    if not weights:
        raise ForecastingError(
            "Weighted moving average requires weights."
        )

    numeric_weights = np.asarray(
        weights,
        dtype=float,
    )

    if np.any(numeric_weights < 0):
        raise ForecastingError(
            "Weighted moving-average weights cannot be negative."
        )

    total_weight = float(
        numeric_weights.sum()
    )

    if total_weight <= 0:
        raise ForecastingError(
            "Weighted moving-average weights must total more than zero."
        )

    numeric_weights = (
        numeric_weights / total_weight
    )

    window = len(
        numeric_weights
    )

    if len(prepared) < window:
        raise ForecastingError(
            "Demand history is shorter than the number of weights."
        )

    recent_values = prepared.iloc[
        -window:
    ].to_numpy(dtype=float)

    forecast_value = float(
        np.dot(
            recent_values,
            numeric_weights,
        )
    )

    fitted_values: list[float] = []

    for index in range(len(prepared)):
        if index < window:
            fitted_values.append(
                float(prepared.iloc[: index + 1].mean())
            )
            continue

        previous_values = prepared.iloc[
            index - window:index
        ].to_numpy(dtype=float)

        fitted_values.append(
            float(
                np.dot(
                    previous_values,
                    numeric_weights,
                )
            )
        )

    return ForecastResult(
        model_name="weighted_moving_average",
        forecast_horizon=forecast_horizon,
        forecast_values=create_constant_forecast(
            forecast_value,
            forecast_horizon,
        ),
        fitted_values=pd.Series(
            fitted_values,
            dtype=float,
        ),
        parameters={
            "weights": numeric_weights.tolist(),
        },
    )