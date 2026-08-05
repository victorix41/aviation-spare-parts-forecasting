"""Tests for specialist advisory agents."""

import pandas as pd

from src.agents.advisory_orchestrator import (
    run_advisory_orchestration,
)
from src.agents.assurance_agent import (
    assure_recommendation,
)
from src.agents.advisory_models import (
    AgentRecommendation,
    EvidenceItem,
)


def create_settings() -> dict:
    """Create representative agent settings."""

    return {
        "governance": {
            "allow_database_writes": False,
            "allow_inventory_changes": False,
            "allow_purchase_order_creation": False,
            "allow_financial_approval": False,
            "require_human_approval": True,
            "require_evidence": True,
            "require_final_assurance": True,
        },
        "thresholds": {
            "executive": {
                "critical_parts_trigger": 1,
                "high_risk_parts_trigger": 1,
                "procurement_value_trigger_usd": 1000,
            },
            "procurement": {
                "urgent_priority_maximum": 2,
                "high_value_order_usd": 5000,
                "long_lead_time_days": 90,
            },
            "finance": {
                "high_total_procurement_value_usd": 1000,
                "high_single_part_value_usd": 5000,
                "low_confidence_value_review_usd": 1000,
            },
            "engineering": {
                "criticality_levels": [
                    "Critical",
                    "High",
                ],
                "low_confidence_requires_review": True,
            },
            "operations": {
                "immediate_stockout_months": 0.5,
                "near_term_stockout_months": 1.5,
            },
            "quality": {
                "require_human_approval_for_all_orders": True,
                "flag_missing_evidence": True,
                "flag_low_confidence_orders": True,
            },
        },
    }


def create_optimisation_data() -> pd.DataFrame:
    """Create representative optimisation data."""

    return pd.DataFrame(
        {
            "part_number": [
                "PN-001",
            ],
            "description": [
                "Bearing",
            ],
            "engineering_criticality": [
                "High",
            ],
            "demand_pattern": [
                "Intermittent",
            ],
            "selected_forecast_model": [
                "croston_sba",
            ],
            "forecast_confidence": [
                "Low",
            ],
            "current_balance": [
                0.0,
            ],
            "reorder_point": [
                5.0,
            ],
            "recommended_order_quantity": [
                10.0,
            ],
            "procurement_value_usd": [
                10000.0,
            ],
            "inventory_value_usd": [
                0.0,
            ],
            "average_lead_time_days": [
                100.0,
            ],
            "estimated_stockout_months": [
                0.0,
            ],
            "stockout_risk": [
                "Critical",
            ],
            "procurement_priority": [
                1,
            ],
            "human_approval_required": [
                True,
            ],
            "recommendation_reason": [
                "Critical stock risk."
            ],
        }
    )


def test_final_assurance_passes_compliant_recommendation() -> None:
    """A compliant recommendation should pass assurance."""

    recommendation = AgentRecommendation(
        recommendation_id="REC-001",
        agent_name="Test Agent",
        target_role="Test Manager",
        recommendation_type="Review",
        priority="High",
        part_number="PN-001",
        title="Test recommendation",
        recommendation="Review the requirement.",
        rationale="Supported by validated evidence.",
        forecast_confidence="Medium",
        evidence=[
            EvidenceItem(
                field_name="stockout_risk",
                value="High",
                source_table=(
                    "inventory_optimisation_results"
                ),
            )
        ],
        human_approval_required=True,
        automatic_action_allowed=False,
        status="Pending review",
    )

    result = assure_recommendation(
        recommendation,
        create_settings(),
    )

    assert result.assurance_status == "Passed"
    assert (
        result.approved_for_management_display
        is True
    )


def test_final_assurance_rejects_automatic_action() -> None:
    """Automatic action must fail assurance."""

    recommendation = AgentRecommendation(
        recommendation_id="REC-002",
        agent_name="Test Agent",
        target_role="Test Manager",
        recommendation_type="Review",
        priority="High",
        part_number="PN-001",
        title="Test recommendation",
        recommendation="Automatically order the part.",
        rationale="Test rationale.",
        forecast_confidence="Medium",
        evidence=[
            EvidenceItem(
                field_name="stockout_risk",
                value="High",
                source_table=(
                    "inventory_optimisation_results"
                ),
            )
        ],
        human_approval_required=False,
        automatic_action_allowed=True,
        status="Automatic",
    )

    result = assure_recommendation(
        recommendation,
        create_settings(),
    )

    assert result.assurance_status == "Failed"
    assert (
        result.approved_for_management_display
        is False
    )


def test_complete_advisory_orchestration() -> None:
    """All specialist agents should produce assured recommendations."""

    optimisation = create_optimisation_data()

    result = run_advisory_orchestration(
        optimisation_data=optimisation,
        procurement_data=optimisation,
        settings=create_settings(),
    )

    assert len(result.recommendations) > 0

    assert len(
        result.assurance_findings
    ) == len(
        result.recommendations
    )

    assert all(
        finding.approved_for_management_display
        for finding
        in result.assurance_findings
    )

    roles = {
        recommendation.target_role
        for recommendation
        in result.recommendations
    }

    assert "Accountable Manager" in roles
    assert "Procurement Manager" in roles
    assert "Finance Manager" in roles
    assert "Engineering Manager" in roles
    assert "Operations Manager" in roles
    assert "Quality Manager" in roles