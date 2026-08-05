"""Registry for the Phase 3.2 forecasting model library."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from src.forecasting.croston import (
    forecast_croston_sba,
)
from src.forecasting.exponential_smoothing import (
    forecast_exponential_smoothing,
)
from src.forecasting.forecast_models import (
    ForecastResult,
)
from src.forecasting.moving_average import (
    forecast_moving_average,
    forecast_weighted_moving_average,
)
from src.forecasting.naive import (
    forecast_naive,
)


ForecastFunction = Callable[
    ...,
    ForecastResult,
]


MODEL_REGISTRY: dict[str, ForecastFunction] = {
    "naive": forecast_naive,
    "moving_average": forecast_moving_average,
    "weighted_moving_average": (
        forecast_weighted_moving_average
    ),
    "exponential_smoothing": (
        forecast_exponential_smoothing
    ),
    "croston_sba": forecast_croston_sba,
}


def list_available_models() -> list[str]:
    """Return available model names."""

    return sorted(
        MODEL_REGISTRY
    )


def run_registered_model(
    model_name: str,
    demand: pd.Series,
    *,
    forecast_horizon: int,
    model_parameters: dict[str, Any] | None = None,
) -> ForecastResult:
    """Execute a registered forecasting model."""

    if model_name not in MODEL_REGISTRY:
        available = ", ".join(
            list_available_models()
        )

        raise ValueError(
            f"Unknown forecasting model: {model_name}. "
            f"Available models: {available}"
        )

    parameters = dict(
        model_parameters or {}
    )

    return MODEL_REGISTRY[
        model_name
    ](
        demand,
        forecast_horizon=forecast_horizon,
        **parameters,
    )