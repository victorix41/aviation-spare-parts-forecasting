"""Tests for the demand analytics engine."""

import pandas as pd

from src.analytics.demand_engine import (
    calculate_average_demand_interval,
    calculate_cv_squared,
    classify_demand_pattern,
    classify_xyz,
    generate_monthly_demand,
    run_demand_analysis,
)


def create_inventory() -> pd.DataFrame:
    """Create a representative inventory master."""

    return pd.DataFrame(
        {
            "part_number": [
                "PN-001",
                "PN-002",
                "PN-003",
            ],
            "description": [
                "Bearing",
                "Seal",
                "Bolt",
            ],
        }
    )


def create_issue_history() -> pd.DataFrame:
    """Create a small representative issue-history dataset."""

    return pd.DataFrame(
        {
            "part_number": [
                "PN-001",
                "PN-001",
                "PN-002",
            ],
            "description": [
                "Bearing",
                "Bearing",
                "Seal",
            ],
            "issue_date": [
                "2026-01-10",
                "2026-03-15",
                "2026-02-05",
            ],
            "quantity_issued": [
                2,
                4,
                3,
            ],
            "unit_price_usd": [
                100.0,
                100.0,
                20.0,
            ],
            "issued_value_usd": [
                200.0,
                400.0,
                60.0,
            ],
        }
    )


def test_monthly_demand_includes_zero_months() -> None:
    """Each part should have one row for every history month."""

    monthly = generate_monthly_demand(
        inventory=create_inventory(),
        issue_history=create_issue_history(),
        history_start_date="2026-01-01",
        history_end_date="2026-03-31",
    )

    assert len(monthly) == 9

    part_one = monthly.loc[
        monthly["part_number"] == "PN-001"
    ]

    assert (
        part_one["quantity_issued"].tolist()
        == [2.0, 0.0, 4.0]
    )


def test_average_demand_interval() -> None:
    """ADI should include zero-demand periods."""

    quantities = pd.Series(
        [2, 0, 4, 0]
    )

    assert (
        calculate_average_demand_interval(
            quantities
        )
        == 2.0
    )


def test_cv_squared_is_zero_for_equal_demand() -> None:
    """Equal positive demand quantities have no variation."""

    assert (
        calculate_cv_squared(
            pd.Series([3, 3, 3])
        )
        == 0.0
    )


def test_demand_pattern_classification() -> None:
    """Demand patterns should follow ADI and CV² rules."""

    assert classify_demand_pattern(
        1.0,
        0.2,
        adi_threshold=1.32,
        cv_squared_threshold=0.49,
    ) == "Smooth"

    assert classify_demand_pattern(
        2.0,
        0.2,
        adi_threshold=1.32,
        cv_squared_threshold=0.49,
    ) == "Intermittent"

    assert classify_demand_pattern(
        2.0,
        0.8,
        adi_threshold=1.32,
        cv_squared_threshold=0.49,
    ) == "Lumpy"


def test_xyz_classification() -> None:
    """XYZ classification should reflect demand variability."""

    assert classify_xyz(
        0.3,
        class_x_cv=0.5,
        class_y_cv=1.0,
    ) == "X"

    assert classify_xyz(
        0.8,
        class_x_cv=0.5,
        class_y_cv=1.0,
    ) == "Y"

    assert classify_xyz(
        1.5,
        class_x_cv=0.5,
        class_y_cv=1.0,
    ) == "Z"


def test_complete_demand_analysis() -> None:
    """The full engine should produce all three outputs."""

    result = run_demand_analysis(
        inventory=create_inventory(),
        issue_history=create_issue_history(),
        history_start_date="2026-01-01",
        history_end_date="2026-03-31",
        adi_threshold=1.32,
        cv_squared_threshold=0.49,
        class_x_cv=0.5,
        class_y_cv=1.0,
        class_a_threshold=0.8,
        class_b_threshold=0.95,
    )

    assert len(result.monthly_demand) == 9
    assert len(result.demand_metrics) == 3
    assert len(result.pareto_analysis) == 3

    assert {
        "abc_class",
        "xyz_class",
        "abc_xyz_class",
        "demand_pattern",
    }.issubset(
        result.demand_metrics.columns
    )