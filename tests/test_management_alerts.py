"""Tests for deterministic management alerts."""

import pandas as pd

from src.analytics.management_alerts import (
    build_assurance_alerts,
    build_inventory_alerts,
    sort_alerts,
)


def test_critical_stockout_creates_alert() -> None:
    """Critical stock risk should create an operations alert."""

    data = pd.DataFrame(
        [
            {
                "part_number": "PN-001",
                "stockout_risk": "Critical",
                "forecast_confidence": "Medium",
                "current_balance": 0,
                "recommended_order_quantity": 10,
                "procurement_value_usd": 5000,
            }
        ]
    )

    alerts = build_inventory_alerts(
        data
    )

    assert any(
        alert.alert_type
        == "Stockout Risk"
        for alert in alerts
    )


def test_low_confidence_high_risk_creates_alert() -> None:
    """Low-confidence high-risk part should require review."""

    data = pd.DataFrame(
        [
            {
                "part_number": "PN-002",
                "stockout_risk": "High",
                "forecast_confidence": "Low",
                "current_balance": 1,
                "recommended_order_quantity": 5,
                "procurement_value_usd": 10000,
            }
        ]
    )

    alerts = build_inventory_alerts(
        data
    )

    assert any(
        alert.alert_type
        == "Forecast Uncertainty"
        for alert in alerts
    )


def test_high_value_procurement_creates_finance_alert() -> None:
    """Large projected spend should create a finance alert."""

    data = pd.DataFrame(
        [
            {
                "part_number": "PN-003",
                "stockout_risk": "Low",
                "forecast_confidence": "Medium",
                "current_balance": 5,
                "recommended_order_quantity": 10,
                "procurement_value_usd": 150000,
            }
        ]
    )

    alerts = build_inventory_alerts(
        data
    )

    assert any(
        alert.target_role
        == "Finance Manager"
        for alert in alerts
    )


def test_failed_assurance_creates_quality_alert() -> None:
    """Failed assurance should create a critical quality alert."""

    data = pd.DataFrame(
        [
            {
                "recommendation_id": "REC-001",
                "assurance_status": "Failed",
                "finding_type": "Governance",
                "finding_message": "Failure",
                "evidence_complete": False,
                "governance_compliant": False,
                "approved_for_management_display": False,
            }
        ]
    )

    alerts = build_assurance_alerts(
        data
    )

    assert len(alerts) == 1

    assert (
        alerts[0].severity
        == "Critical"
    )


def test_alert_sorting_places_critical_first() -> None:
    """Critical alerts should sort before high alerts."""

    data = pd.DataFrame(
        [
            {
                "part_number": "PN-HIGH",
                "stockout_risk": "High",
                "forecast_confidence": "Low",
                "current_balance": 1,
                "recommended_order_quantity": 5,
                "procurement_value_usd": 10000,
            },
            {
                "part_number": "PN-CRITICAL",
                "stockout_risk": "Critical",
                "forecast_confidence": "Medium",
                "current_balance": 0,
                "recommended_order_quantity": 5,
                "procurement_value_usd": 10000,
            },
        ]
    )

    alerts = sort_alerts(
        build_inventory_alerts(
            data
        )
    )

    assert (
        alerts[0].severity
        == "Critical"
    )

def test_custom_finance_threshold_is_used() -> None:
    """Finance threshold should be configurable."""

    data = pd.DataFrame(
        [
            {
                "part_number": "PN-100",
                "stockout_risk": "Low",
                "forecast_confidence": "Medium",
                "current_balance": 10,
                "recommended_order_quantity": 1,
                "procurement_value_usd": 75000,
            }
        ]
    )

    alerts = build_inventory_alerts(
        data,
        finance_high_value_usd=50000,
    )

    assert any(
        alert.target_role
        == "Finance Manager"
        for alert in alerts
    )


def test_custom_engineering_risk_levels_are_used() -> None:
    """Engineering alert levels should be configurable."""

    data = pd.DataFrame(
        [
            {
                "part_number": "PN-200",
                "stockout_risk": "Medium",
                "forecast_confidence": "Low",
                "current_balance": 2,
                "recommended_order_quantity": 3,
                "procurement_value_usd": 5000,
            }
        ]
    )

    alerts = build_inventory_alerts(
        data,
        engineering_high_risks={
            "Medium",
        },
        engineering_low_confidence={
            "Low",
        },
    )

    assert any(
        alert.alert_type
        == "Forecast Uncertainty"
        for alert in alerts
    )