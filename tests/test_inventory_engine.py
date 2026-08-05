"""Tests for inventory optimisation."""

import pandas as pd
import pytest

from src.optimisation.inventory_engine import (
    calculate_economic_order_quantity,
    calculate_lead_time_days,
    calculate_months_of_cover,
    calculate_safety_stock,
    calculate_service_level_z_score,
    classify_stockout_risk,
    prepare_inventory_summary,
    run_inventory_optimisation,
)


def create_settings() -> dict:
    """Create representative optimisation settings."""

    return {
        "days_per_month": 30.4375,
        "default_lead_time_days": 45,
        "minimum_lead_time_days": 1,
        "service_levels": {
            "critical": 0.99,
            "high": 0.97,
            "medium": 0.95,
            "low": 0.90,
            "unspecified": 0.95,
        },
        "eoq": {
            "enabled": True,
            "ordering_cost_usd": 150.0,
            "annual_holding_rate": 0.25,
        },
        "target_stock": {
            "planning_horizon_months": 12,
            "include_safety_stock": True,
        },
        "risk_thresholds": {
            "critical_months_cover": 0.0,
            "high_months_cover": 1.5,
            "medium_months_cover": 3.0,
        },
        "procurement_priority": {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 4,
        },
        "governance": {
            "automatic_purchase_orders": False,
            "human_approval_required": True,
        },
    }


def test_service_level_z_score() -> None:
    """A 95% service level should produce about 1.645."""

    assert calculate_service_level_z_score(
        0.95
    ) == pytest.approx(
        1.64485,
        rel=1e-4,
    )


def test_lead_time_calculation() -> None:
    """Lead time should equal the date difference."""

    result = calculate_lead_time_days(
        "2026-01-01",
        "2026-01-31",
        default_lead_time_days=45,
        minimum_lead_time_days=1,
    )

    assert result == 30.0


def test_safety_stock_is_non_negative() -> None:
    """Safety stock should never be negative."""

    result = calculate_safety_stock(
        demand_standard_deviation=2.0,
        lead_time_months=1.5,
        z_score=1.645,
    )

    assert result > 0


def test_eoq_calculation() -> None:
    """EOQ should produce a positive result."""

    result = calculate_economic_order_quantity(
        annual_demand=120,
        ordering_cost_usd=150,
        unit_price_usd=100,
        annual_holding_rate=0.25,
    )

    assert result > 0


def test_months_of_cover() -> None:
    """Stock cover should equal balance divided by monthly demand."""

    assert calculate_months_of_cover(
        current_balance=12,
        average_monthly_demand=3,
    ) == 4.0


def test_zero_balance_is_critical() -> None:
    """Zero stock should be classified as critical."""

    risk = classify_stockout_risk(
        current_balance=0,
        reorder_point=5,
        months_of_cover=0,
        critical_months_cover=0,
        high_months_cover=1.5,
        medium_months_cover=3.0,
    )

    assert risk == "Critical"


def test_duplicate_inventory_records_are_aggregated() -> None:
    """Multiple lots for a part should be aggregated."""

    inventory = pd.DataFrame(
        {
            "part_number": [
                "PN-001",
                "PN-001",
            ],
            "description": [
                "Bearing",
                "Bearing",
            ],
            "unit_price_usd": [
                100.0,
                100.0,
            ],
            "balance_quantity": [
                3,
                4,
            ],
            "purchase_order_date": [
                "2026-01-01",
                "2026-02-01",
            ],
            "delivery_order_date": [
                "2026-01-31",
                "2026-03-03",
            ],
        }
    )

    result = prepare_inventory_summary(
        inventory,
        default_lead_time_days=45,
        minimum_lead_time_days=1,
    )

    assert len(result) == 1
    assert result.iloc[0][
        "inventory_record_count"
    ] == 2
    assert result.iloc[0][
        "current_balance"
    ] == 7


def test_complete_inventory_optimisation() -> None:
    """The complete engine should produce one result per forecast part."""

    inventory = pd.DataFrame(
        {
            "part_number": [
                "PN-001",
            ],
            "description": [
                "Bearing",
            ],
            "unit_price_usd": [
                100.0,
            ],
            "balance_quantity": [
                2,
            ],
            "purchase_order_date": [
                "2026-01-01",
            ],
            "delivery_order_date": [
                "2026-01-31",
            ],
        }
    )

    demand_metrics = pd.DataFrame(
        {
            "part_number": [
                "PN-001",
            ],
            "description": [
                "Bearing",
            ],
            "average_monthly_demand": [
                2.0,
            ],
            "demand_standard_deviation": [
                1.0,
            ],
            "demand_pattern": [
                "Intermittent",
            ],
            "engineering_criticality": [
                "High",
            ],
        }
    )

    final_forecasts = pd.DataFrame(
        {
            "part_number": [
                "PN-001",
            ],
            "description": [
                "Bearing",
            ],
            "demand_pattern": [
                "Intermittent",
            ],
            "selected_model": [
                "croston_sba",
            ],
            "forecast_confidence": [
                "Medium",
            ],
            "forecast_3m": [
                6.0,
            ],
            "forecast_6m": [
                12.0,
            ],
            "forecast_12m": [
                24.0,
            ],
        }
    )

    result = run_inventory_optimisation(
        inventory=inventory,
        demand_metrics=demand_metrics,
        final_forecasts=final_forecasts,
        settings=create_settings(),
    )

    assert len(result) == 1
    assert (
        result.iloc[0][
            "recommended_order_quantity"
        ]
        > 0
    )
    assert (
        result.iloc[0][
            "human_approval_required"
        ]
        is True
        or bool(
            result.iloc[0][
                "human_approval_required"
            ]
        )
        is True
    )