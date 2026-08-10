"""Tests for deterministic forecast explainability."""

from src.forecasting.explainability import (
    build_confidence_explanation,
    build_forecast_explanation,
    build_management_interpretation,
)


def test_low_confidence_interpretation() -> None:
    """Low confidence should require additional review."""

    result = (
        build_management_interpretation(
            "Low"
        )
    )

    assert (
        "additional management review"
        in result
    )


def test_high_confidence_still_requires_review() -> None:
    """High confidence must not imply automatic action."""

    result = (
        build_management_interpretation(
            "High"
        )
    )

    assert (
        "authorised procurement review"
        in result
    )


def test_confidence_explanation_uses_history() -> None:
    """Confidence explanation should use stored demand evidence."""

    result = (
        build_confidence_explanation(
            forecast_confidence="Low",
            demand_pattern="Intermittent",
            active_demand_months=10,
            zero_demand_months=26,
            history_months=36,
        )
    )

    assert "10 of 36" in result
    assert "26 months" in result
    assert "Intermittent" in result


def test_forecast_explanation_uses_stored_reason() -> None:
    """The engine should preserve the stored model-selection reason."""

    selected_model_record = {
        "part_number": "PS172306-519",
        "selected_model": (
            "moving_average"
        ),
        "demand_pattern": (
            "Intermittent"
        ),
        "forecast_confidence": "Low",
        "selection_metric": "wape",
        "selection_score": 1.074074,
        "successful_model_count": 5,
        "selection_reason": (
            "moving_average achieved the "
            "lowest WAPE score."
        ),
    }

    demand_record = {
        "history_months": 36,
        "active_demand_months": 10,
        "zero_demand_months": 26,
        "demand_pattern": (
            "Intermittent"
        ),
    }

    result = build_forecast_explanation(
        selected_model_record=(
            selected_model_record
        ),
        demand_record=demand_record,
    )

    assert (
        result["selected_model"]
        == "moving_average"
    )

    assert (
        result["selection_reason"]
        == selected_model_record[
            "selection_reason"
        ]
    )

    assert (
        result["successful_model_count"]
        == 5
    )


def test_governance_statement_blocks_automatic_action() -> None:
    """Explainability should retain human-review governance."""

    result = build_forecast_explanation(
        selected_model_record={
            "part_number": "PN-001",
            "selected_model": "naive",
            "forecast_confidence": "Medium",
            "demand_pattern": "Intermittent",
            "selection_reason": "Stored reason.",
        },
        demand_record={},
    )

    statement = result[
        "governance_statement"
    ]

    assert (
        "does not authorise automatic purchasing"
        in statement
    )

    assert (
        "human review"
        in statement
    )