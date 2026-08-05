"""Tests for forecast-accuracy metrics."""

import pandas as pd
import pytest

from src.forecasting.accuracy_metrics import (
    calculate_forecast_accuracy,
)


def test_perfect_forecast_has_zero_error() -> None:
    """A perfect forecast should have no error."""

    result = calculate_forecast_accuracy(
        actual=pd.Series([1, 2, 3]),
        forecast=pd.Series([1, 2, 3]),
    )

    assert result.mae == 0.0
    assert result.rmse == 0.0
    assert result.wape == 0.0
    assert result.bias == 0.0


def test_forecast_metrics() -> None:
    """Metrics should reflect forecast errors."""

    result = calculate_forecast_accuracy(
        actual=pd.Series([2, 0, 4]),
        forecast=pd.Series([1, 1, 3]),
    )

    assert result.mae == pytest.approx(1.0)
    assert result.rmse == pytest.approx(1.0)
    assert result.wape == pytest.approx(3 / 6)
    assert result.bias == pytest.approx(-1 / 3)


def test_zero_actual_demand_is_safe() -> None:
    """A zero-demand validation period should not divide by zero."""

    result = calculate_forecast_accuracy(
        actual=pd.Series([0, 0, 0]),
        forecast=pd.Series([1, 1, 1]),
    )

    assert result.actual_total == 0.0
    assert result.wape == 3.0