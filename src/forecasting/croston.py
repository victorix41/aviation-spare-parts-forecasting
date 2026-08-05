"""Croston SBA forecasting for intermittent spare-parts demand."""

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


def forecast_croston_sba(
    demand: pd.Series,
    *,
    forecast_horizon: int,
    alpha: float = 0.10,
) -> ForecastResult:
    """
    Forecast intermittent demand using Croston's method with SBA correction.

    SBA applies the correction factor ``1 - alpha / 2`` to reduce the
    positive bias associated with the original Croston estimate.
    """

    validate_forecast_horizon(
        forecast_horizon
    )

    prepared = prepare_demand_series(
        demand
    )

    if not 0 < alpha <= 1:
        raise ForecastingError(
            "Croston alpha must be greater than zero "
            "and no greater than one."
        )

    positive_positions = prepared[
        prepared > 0
    ].index.tolist()

    if not positive_positions:
        zero_series = pd.Series(
            [0.0] * len(prepared),
            dtype=float,
        )

        return ForecastResult(
            model_name="croston_sba",
            forecast_horizon=forecast_horizon,
            forecast_values=create_constant_forecast(
                0.0,
                forecast_horizon,
            ),
            fitted_values=zero_series,
            parameters={
                "alpha": alpha,
                "sba_correction": (
                    1 - alpha / 2
                ),
            },
        )

    first_position = int(
        positive_positions[0]
    )

    demand_estimate = float(
        prepared.iloc[first_position]
    )

    interval_estimate = float(
        first_position + 1
    )

    interval_counter = 1.0

    correction_factor = (
        1 - alpha / 2
    )

    fitted_values: list[float] = []

    for observation in prepared:
        current_forecast = (
            correction_factor
            * demand_estimate
            / interval_estimate
        )

        fitted_values.append(
            max(
                0.0,
                float(current_forecast),
            )
        )

        if observation > 0:
            demand_estimate = (
                alpha
                * float(observation)
                + (1 - alpha)
                * demand_estimate
            )

            interval_estimate = (
                alpha
                * interval_counter
                + (1 - alpha)
                * interval_estimate
            )

            interval_counter = 1.0
        else:
            interval_counter += 1.0

    forecast_value = (
        correction_factor
        * demand_estimate
        / interval_estimate
    )

    return ForecastResult(
        model_name="croston_sba",
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
            "alpha": alpha,
            "sba_correction": correction_factor,
            "final_demand_estimate": demand_estimate,
            "final_interval_estimate": interval_estimate,
        },
    )