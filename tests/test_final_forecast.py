"""Tests for final future forecast generation."""

import pandas as pd

from src.forecasting.final_forecast import (
    generate_final_forecast,
)


def test_generate_final_forecast() -> None:
    """A selected model should produce forecast horizons."""

    result = generate_final_forecast(
        part_number="PN-001",
        description="Bearing",
        demand_pattern="Intermittent",
        selected_model="croston_sba",
        forecast_confidence="Medium",
        demand=pd.Series(
            [
                0, 2, 0, 0, 2, 0,
                0, 3, 0, 0, 2, 0,
            ]
        ),
        forecast_horizon=12,
        model_parameters={
            "alpha": 0.1,
        },
    )

    assert len(
        result.forecast_values
    ) == 12

    assert result.forecast_3m >= 0
    assert result.forecast_6m >= result.forecast_3m
    assert result.forecast_12m >= result.forecast_6m

    assert (
        result.advisory_status
        == "Decision support only — human review required"
    )