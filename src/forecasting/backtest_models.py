"""Typed models for forecast backtesting and model selection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ModelBacktestResult:
    """Backtest result for one model and one spare part."""

    part_number: str
    description: str
    demand_pattern: str
    model_name: str
    status: str
    rejection_reason: str | None
    training_months: int
    validation_months: int
    training_total_demand: float
    validation_actual_total: float | None
    validation_forecast_total: float | None
    mae: float | None
    rmse: float | None
    wape: float | None
    bias: float | None
    model_rank: int | None
    selected: bool
    model_parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable result."""

        return asdict(self)


@dataclass(frozen=True)
class SelectedModelResult:
    """Selected forecasting model for one spare part."""

    part_number: str
    description: str
    demand_pattern: str
    selected_model: str
    selection_metric: str
    selection_score: float
    mae: float
    rmse: float
    wape: float
    bias: float
    validation_actual_total: float
    validation_forecast_total: float
    successful_model_count: int
    rejected_model_count: int
    forecast_confidence: str
    selection_reason: str

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable result."""

        return asdict(self)