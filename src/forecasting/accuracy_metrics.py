"""Forecast accuracy metrics for aviation spare-parts demand."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.forecasting.forecast_utils import ForecastingError


@dataclass(frozen=True)
class ForecastAccuracy:
    """Accuracy metrics for one backtested forecast."""

    mae: float
    rmse: float
    wape: float
    bias: float
    actual_total: float
    forecast_total: float
    absolute_error_total: float

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""

        return asdict(self)


def prepare_metric_series(
    actual: pd.Series,
    forecast: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """Validate and align actual and forecast values."""

    if not isinstance(actual, pd.Series):
        raise ForecastingError(
            "Actual values must be provided as a pandas Series."
        )

    if not isinstance(forecast, pd.Series):
        raise ForecastingError(
            "Forecast values must be provided as a pandas Series."
        )

    if actual.empty:
        raise ForecastingError(
            "Actual values contain no observations."
        )

    if len(actual) != len(forecast):
        raise ForecastingError(
            "Actual and forecast series must have the same length."
        )

    actual_values = pd.to_numeric(
        actual,
        errors="coerce",
    )

    forecast_values = pd.to_numeric(
        forecast,
        errors="coerce",
    )

    if actual_values.isna().any():
        raise ForecastingError(
            "Actual values contain invalid numeric data."
        )

    if forecast_values.isna().any():
        raise ForecastingError(
            "Forecast values contain invalid numeric data."
        )

    if not np.isfinite(actual_values).all():
        raise ForecastingError(
            "Actual values contain non-finite data."
        )

    if not np.isfinite(forecast_values).all():
        raise ForecastingError(
            "Forecast values contain non-finite data."
        )

    return (
        actual_values.astype(float).reset_index(drop=True),
        forecast_values.astype(float).reset_index(drop=True),
    )


def calculate_forecast_accuracy(
    actual: pd.Series,
    forecast: pd.Series,
) -> ForecastAccuracy:
    """Calculate MAE, RMSE, WAPE and forecast bias."""

    actual_values, forecast_values = prepare_metric_series(
        actual,
        forecast,
    )

    errors = forecast_values - actual_values
    absolute_errors = errors.abs()

    mae = float(
        absolute_errors.mean()
    )

    rmse = float(
        np.sqrt(
            np.mean(
                np.square(errors)
            )
        )
    )

    actual_total = float(
        actual_values.sum()
    )

    forecast_total = float(
        forecast_values.sum()
    )

    absolute_error_total = float(
        absolute_errors.sum()
    )

    if actual_total > 0:
        wape = (
            absolute_error_total
            / actual_total
        )
    else:
        # No actual demand occurred during validation.
        # Use absolute forecast error as the ranking score.
        wape = absolute_error_total

    bias = float(
        errors.mean()
    )

    return ForecastAccuracy(
        mae=mae,
        rmse=rmse,
        wape=float(wape),
        bias=bias,
        actual_total=actual_total,
        forecast_total=forecast_total,
        absolute_error_total=absolute_error_total,
    )