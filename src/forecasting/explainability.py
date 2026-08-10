"""Deterministic forecast explainability utilities."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _safe_float(
    value: Any,
) -> float | None:
    """Convert a value to float when possible."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(
    value: Any,
) -> int | None:
    """Convert a value to integer when possible."""

    number = _safe_float(value)

    if number is None:
        return None

    return int(number)


def build_confidence_explanation(
    *,
    forecast_confidence: str | None,
    demand_pattern: str | None,
    active_demand_months: int | None,
    zero_demand_months: int | None,
    history_months: int | None,
) -> str:
    """Explain forecast confidence using stored evidence."""

    confidence = (
        forecast_confidence
        or "Unspecified"
    )

    pattern = (
        demand_pattern
        or "Unspecified"
    )

    evidence: list[str] = []

    if (
        active_demand_months is not None
        and history_months is not None
    ):
        evidence.append(
            f"demand occurred in "
            f"{active_demand_months} of "
            f"{history_months} historical months"
        )

    if zero_demand_months is not None:
        evidence.append(
            f"{zero_demand_months} months "
            f"recorded zero demand"
        )

    if evidence:
        evidence_text = "; ".join(
            evidence
        )

        return (
            f"Forecast confidence is {confidence}. "
            f"The demand pattern is {pattern}. "
            f"Historical evidence shows that "
            f"{evidence_text}."
        )

    return (
        f"Forecast confidence is {confidence}. "
        f"The stored demand pattern is {pattern}."
    )


def build_management_interpretation(
    forecast_confidence: str | None,
) -> str:
    """Return management guidance for confidence level."""

    confidence = (
        forecast_confidence
        or ""
    ).strip().lower()

    if confidence == "low":
        return (
            "Forecast uncertainty is elevated. "
            "Use the forecast as planning guidance "
            "and apply additional management review "
            "before procurement commitment."
        )

    if confidence == "medium":
        return (
            "The forecast provides useful planning "
            "guidance, but procurement decisions "
            "should still consider current inventory, "
            "lead time, engineering criticality and "
            "authorised human review."
        )

    if confidence == "high":
        return (
            "The forecast has comparatively stronger "
            "analytical confidence, but it remains "
            "decision support and does not replace "
            "authorised procurement review."
        )

    return (
        "The forecast is decision support only. "
        "Authorised human review is required before "
        "procurement action."
    )


def build_forecast_explanation(
    *,
    selected_model_record: dict[str, Any],
    demand_record: dict[str, Any],
) -> dict[str, Any]:
    """Build a deterministic forecast explanation."""

    selected_model = (
        selected_model_record.get(
            "selected_model"
        )
    )

    demand_pattern = (
        selected_model_record.get(
            "demand_pattern"
        )
        or demand_record.get(
            "demand_pattern"
        )
    )

    confidence = (
        selected_model_record.get(
            "forecast_confidence"
        )
    )

    selection_reason = (
        selected_model_record.get(
            "selection_reason"
        )
    )

    successful_models = _safe_int(
        selected_model_record.get(
            "successful_model_count"
        )
    )

    selection_metric = (
        selected_model_record.get(
            "selection_metric"
        )
    )

    selection_score = _safe_float(
        selected_model_record.get(
            "selection_score"
        )
    )

    active_months = _safe_int(
        demand_record.get(
            "active_demand_months"
        )
    )

    zero_months = _safe_int(
        demand_record.get(
            "zero_demand_months"
        )
    )

    history_months = _safe_int(
        demand_record.get(
            "history_months"
        )
    )

    return {
        "part_number": (
            selected_model_record.get(
                "part_number"
            )
        ),
        "selected_model": selected_model,
        "forecast_confidence": confidence,
        "demand_pattern": demand_pattern,
        "selection_metric": selection_metric,
        "selection_score": selection_score,
        "successful_model_count": successful_models,
        "selection_reason": selection_reason,
        "confidence_explanation": (
            build_confidence_explanation(
                forecast_confidence=confidence,
                demand_pattern=demand_pattern,
                active_demand_months=active_months,
                zero_demand_months=zero_months,
                history_months=history_months,
            )
        ),
        "management_interpretation": (
            build_management_interpretation(
                confidence
            )
        ),
        "governance_statement": (
            "This explanation is derived from stored "
            "forecasting and demand-analysis results. "
            "It does not authorise automatic purchasing "
            "or replace authorised human review."
        ),
    }