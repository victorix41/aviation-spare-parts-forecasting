"""Backtesting and automatic model selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.forecasting.accuracy_metrics import (
    calculate_forecast_accuracy,
)
from src.forecasting.backtest_models import (
    ModelBacktestResult,
    SelectedModelResult,
)
from src.forecasting.forecast_models import ForecastResult
from src.forecasting.forecast_utils import (
    ForecastingError,
    prepare_demand_series,
)
from src.forecasting.model_registry import (
    run_registered_model,
)


@dataclass(frozen=True)
class PartModelSelectionResult:
    """Complete model-selection output for one spare part."""

    backtest_results: list[ModelBacktestResult]
    selected_model: SelectedModelResult | None


def split_train_validation(
    demand: pd.Series,
    *,
    validation_months: int,
    minimum_training_months: int,
) -> tuple[pd.Series, pd.Series]:
    """Split demand into training and validation periods."""

    prepared = prepare_demand_series(
        demand
    )

    if validation_months <= 0:
        raise ForecastingError(
            "Validation months must be greater than zero."
        )

    if minimum_training_months <= 0:
        raise ForecastingError(
            "Minimum training months must be greater than zero."
        )

    required_months = (
        validation_months
        + minimum_training_months
    )

    if len(prepared) < required_months:
        raise ForecastingError(
            "Demand history is too short for backtesting. "
            f"At least {required_months} months are required."
        )

    training = prepared.iloc[
        :-validation_months
    ].reset_index(drop=True)

    validation = prepared.iloc[
        -validation_months:
    ].reset_index(drop=True)

    return training, validation


def determine_forecast_confidence(
    *,
    active_demand_months: int,
    successful_model_count: int,
    selection_score: float,
) -> str:
    """Determine a transparent forecast-confidence category."""

    if successful_model_count == 0:
        return "Not available"

    if active_demand_months >= 18 and selection_score <= 0.50:
        return "High"

    if active_demand_months >= 8 and selection_score <= 1.00:
        return "Medium"

    return "Low"


def model_selection_reason(
    *,
    model_name: str,
    primary_metric: str,
    score: float,
    successful_model_count: int,
) -> str:
    """Create an explainable selection statement."""

    return (
        f"{model_name} achieved the lowest {primary_metric.upper()} "
        f"score of {score:.4f} among "
        f"{successful_model_count} successful candidate models."
    )


def run_model_backtest(
    *,
    part_number: str,
    description: str,
    demand_pattern: str,
    model_name: str,
    training: pd.Series,
    validation: pd.Series,
    model_parameters: dict[str, Any],
) -> ModelBacktestResult:
    """Backtest one model against the validation period."""

    try:
        forecast_result: ForecastResult = run_registered_model(
            model_name=model_name,
            demand=training,
            forecast_horizon=len(validation),
            model_parameters=model_parameters,
        )

        accuracy = calculate_forecast_accuracy(
            actual=validation,
            forecast=forecast_result.forecast_values,
        )

        return ModelBacktestResult(
            part_number=part_number,
            description=description,
            demand_pattern=demand_pattern,
            model_name=model_name,
            status="successful",
            rejection_reason=None,
            training_months=len(training),
            validation_months=len(validation),
            training_total_demand=float(
                training.sum()
            ),
            validation_actual_total=(
                accuracy.actual_total
            ),
            validation_forecast_total=(
                accuracy.forecast_total
            ),
            mae=accuracy.mae,
            rmse=accuracy.rmse,
            wape=accuracy.wape,
            bias=accuracy.bias,
            model_rank=None,
            selected=False,
            model_parameters=model_parameters,
        )

    except Exception as exc:
        return ModelBacktestResult(
            part_number=part_number,
            description=description,
            demand_pattern=demand_pattern,
            model_name=model_name,
            status="rejected",
            rejection_reason=str(exc),
            training_months=len(training),
            validation_months=len(validation),
            training_total_demand=float(
                training.sum()
            ),
            validation_actual_total=float(
                validation.sum()
            ),
            validation_forecast_total=None,
            mae=None,
            rmse=None,
            wape=None,
            bias=None,
            model_rank=None,
            selected=False,
            model_parameters=model_parameters,
        )


def rank_backtest_results(
    results: list[ModelBacktestResult],
    *,
    primary_metric: str,
    tie_break_order: list[str],
) -> list[ModelBacktestResult]:
    """Rank successful models using the configured metric."""

    valid_metrics = {
        "mae",
        "rmse",
        "wape",
    }

    if primary_metric not in valid_metrics:
        raise ForecastingError(
            "Primary model-selection metric must be one of: "
            + ", ".join(sorted(valid_metrics))
        )

    successful = [
        result
        for result in results
        if result.status == "successful"
    ]

    rejected = [
        result
        for result in results
        if result.status != "successful"
    ]

    tie_break_positions = {
        model_name: index
        for index, model_name
        in enumerate(tie_break_order)
    }

    def sort_key(
        result: ModelBacktestResult,
    ) -> tuple[float, int]:
        metric_value = getattr(
            result,
            primary_metric,
        )

        score = (
            float(metric_value)
            if metric_value is not None
            and np.isfinite(metric_value)
            else float("inf")
        )

        tie_position = tie_break_positions.get(
            result.model_name,
            len(tie_break_positions),
        )

        return score, tie_position

    successful = sorted(
        successful,
        key=sort_key,
    )

    ranked_results: list[ModelBacktestResult] = []

    for rank, result in enumerate(
        successful,
        start=1,
    ):
        ranked_results.append(
            ModelBacktestResult(
                **{
                    **result.to_dict(),
                    "model_rank": rank,
                    "selected": rank == 1,
                }
            )
        )

    ranked_results.extend(
        rejected
    )

    return ranked_results


def select_best_model(
    ranked_results: list[ModelBacktestResult],
    *,
    primary_metric: str,
    active_demand_months: int,
) -> SelectedModelResult | None:
    """Create the selected-model record."""

    successful = [
        result
        for result in ranked_results
        if result.status == "successful"
    ]

    rejected_count = sum(
        result.status != "successful"
        for result in ranked_results
    )

    if not successful:
        return None

    winner = min(
        successful,
        key=lambda result: (
            result.model_rank
            if result.model_rank is not None
            else float("inf")
        ),
    )

    score_value = getattr(
        winner,
        primary_metric,
    )

    if score_value is None:
        return None

    confidence = determine_forecast_confidence(
        active_demand_months=active_demand_months,
        successful_model_count=len(successful),
        selection_score=float(score_value),
    )

    return SelectedModelResult(
        part_number=winner.part_number,
        description=winner.description,
        demand_pattern=winner.demand_pattern,
        selected_model=winner.model_name,
        selection_metric=primary_metric,
        selection_score=float(score_value),
        mae=float(winner.mae or 0.0),
        rmse=float(winner.rmse or 0.0),
        wape=float(winner.wape or 0.0),
        bias=float(winner.bias or 0.0),
        validation_actual_total=float(
            winner.validation_actual_total or 0.0
        ),
        validation_forecast_total=float(
            winner.validation_forecast_total or 0.0
        ),
        successful_model_count=len(successful),
        rejected_model_count=rejected_count,
        forecast_confidence=confidence,
        selection_reason=model_selection_reason(
            model_name=winner.model_name,
            primary_metric=primary_metric,
            score=float(score_value),
            successful_model_count=len(successful),
        ),
    )


def run_part_model_selection(
    *,
    part_number: str,
    description: str,
    demand_pattern: str,
    active_demand_months: int,
    demand: pd.Series,
    validation_months: int,
    minimum_training_months: int,
    model_configurations: dict[str, dict[str, Any]],
    primary_metric: str,
    tie_break_order: list[str],
) -> PartModelSelectionResult:
    """Backtest all models and select the best model for one part."""

    training, validation = split_train_validation(
        demand,
        validation_months=validation_months,
        minimum_training_months=minimum_training_months,
    )

    results = [
        run_model_backtest(
            part_number=part_number,
            description=description,
            demand_pattern=demand_pattern,
            model_name=model_name,
            training=training,
            validation=validation,
            model_parameters=parameters,
        )
        for model_name, parameters
        in model_configurations.items()
    ]

    ranked_results = rank_backtest_results(
        results,
        primary_metric=primary_metric,
        tie_break_order=tie_break_order,
    )

    selected = select_best_model(
        ranked_results,
        primary_metric=primary_metric,
        active_demand_months=active_demand_months,
    )

    return PartModelSelectionResult(
        backtest_results=ranked_results,
        selected_model=selected,
    )