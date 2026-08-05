"""Tests for the Phase 3.2 forecasting models."""

import pandas as pd
import pytest

from src.forecasting.croston import (
    forecast_croston_sba,
)
from src.forecasting.exponential_smoothing import (
    forecast_exponential_smoothing,
)
from src.forecasting.forecast_utils import (
    ForecastingError,
)
from src.forecasting.model_registry import (
    list_available_models,
    run_registered_model,
)
from src.forecasting.moving_average import (
    forecast_moving_average,
    forecast_weighted_moving_average,
)
from src.forecasting.naive import (
    forecast_naive,
)


def test_naive_forecast_uses_latest_value() -> None:
    """Naïve forecast should repeat the last observation."""

    demand = pd.Series(
        [1, 2, 5],
    )

    result = forecast_naive(
        demand,
        forecast_horizon=3,
    )

    assert result.forecast_values.tolist() == [
        5.0,
        5.0,
        5.0,
    ]


def test_moving_average_forecast() -> None:
    """Moving average should use the latest configured window."""

    demand = pd.Series(
        [1, 2, 3, 6],
    )

    result = forecast_moving_average(
        demand,
        forecast_horizon=2,
        window=3,
    )

    assert result.forecast_values.tolist() == [
        pytest.approx(
            11 / 3,
        ),
        pytest.approx(
            11 / 3,
        ),
    ]


def test_weighted_moving_average() -> None:
    """The most recent observation should receive the final weight."""

    demand = pd.Series(
        [1, 2, 3],
    )

    result = (
        forecast_weighted_moving_average(
            demand,
            forecast_horizon=2,
            weights=[
                0.2,
                0.3,
                0.5,
            ],
        )
    )

    expected = (
        1 * 0.2
        + 2 * 0.3
        + 3 * 0.5
    )

    assert result.forecast_values.iloc[
        0
    ] == pytest.approx(expected)


def test_exponential_smoothing_forecast() -> None:
    """Simple exponential smoothing should return non-negative values."""

    result = (
        forecast_exponential_smoothing(
            pd.Series(
                [0, 2, 0, 4],
            ),
            forecast_horizon=3,
            smoothing_level=0.3,
        )
    )

    assert len(
        result.forecast_values
    ) == 3

    assert result.forecast_values.ge(
        0
    ).all()


def test_croston_returns_zero_for_no_demand() -> None:
    """Croston should forecast zero when no demand has occurred."""

    result = forecast_croston_sba(
        pd.Series(
            [0, 0, 0, 0],
        ),
        forecast_horizon=3,
        alpha=0.1,
    )

    assert result.forecast_values.tolist() == [
        0.0,
        0.0,
        0.0,
    ]


def test_croston_handles_intermittent_demand() -> None:
    """Croston SBA should return a positive intermittent forecast."""

    result = forecast_croston_sba(
        pd.Series(
            [
                0,
                3,
                0,
                0,
                3,
                0,
            ]
        ),
        forecast_horizon=3,
        alpha=0.1,
    )

    assert len(
        result.forecast_values
    ) == 3

    assert result.forecast_values.iloc[
        0
    ] > 0


def test_negative_demand_is_rejected() -> None:
    """Forecasts must not accept negative spare-parts demand."""

    with pytest.raises(
        ForecastingError,
        match="negative",
    ):
        forecast_naive(
            pd.Series(
                [1, -1, 2],
            ),
            forecast_horizon=2,
        )


def test_model_registry() -> None:
    """All Phase 3.2 models should be registered."""

    models = list_available_models()

    assert {
        "naive",
        "moving_average",
        "weighted_moving_average",
        "exponential_smoothing",
        "croston_sba",
    }.issubset(
        models
    )

    result = run_registered_model(
        model_name="naive",
        demand=pd.Series(
            [1, 2, 3],
        ),
        forecast_horizon=2,
    )

    assert result.model_name == "naive"