"""Tests for backtesting and model selection."""

import pandas as pd

from src.forecasting.backtesting import (
    rank_backtest_results,
    run_part_model_selection,
    split_train_validation,
)


def test_train_validation_split() -> None:
    """Demand should split into the configured periods."""

    demand = pd.Series(
        range(18),
        dtype=float,
    )

    training, validation = (
        split_train_validation(
            demand,
            validation_months=6,
            minimum_training_months=12,
        )
    )

    assert len(training) == 12
    assert len(validation) == 6

    assert validation.tolist() == [
        12.0,
        13.0,
        14.0,
        15.0,
        16.0,
        17.0,
    ]


def test_part_model_selection_returns_winner() -> None:
    """At least one model should be selected."""

    demand = pd.Series(
        [
            0, 2, 0, 0, 2, 0,
            0, 3, 0, 0, 2, 0,
            0, 2, 0, 0, 3, 0,
        ],
        dtype=float,
    )

    result = run_part_model_selection(
        part_number="PN-001",
        description="Bearing",
        demand_pattern="Intermittent",
        active_demand_months=5,
        demand=demand,
        validation_months=6,
        minimum_training_months=12,
        model_configurations={
            "naive": {},
            "moving_average": {
                "window": 3,
            },
            "croston_sba": {
                "alpha": 0.1,
            },
        },
        primary_metric="wape",
        tie_break_order=[
            "croston_sba",
            "moving_average",
            "naive",
        ],
    )

    assert len(
        result.backtest_results
    ) == 3

    assert (
        result.selected_model
        is not None
    )

    assert (
        result.selected_model.selected_model
        in {
            "naive",
            "moving_average",
            "croston_sba",
        }
    )

    selected_rows = [
        row
        for row in result.backtest_results
        if row.selected
    ]

    assert len(selected_rows) == 1