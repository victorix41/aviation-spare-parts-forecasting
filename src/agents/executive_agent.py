"""Executive advisory agent for the Accountable Manager."""

from __future__ import annotations

import pandas as pd

from src.agents.advisory_models import (
    AgentRecommendation,
)
from src.agents.advisory_utils import (
    create_recommendation_id,
    evidence,
)


AGENT_NAME = "Executive Agent"
TARGET_ROLE = "Accountable Manager"


def generate_executive_recommendations(
    optimisation_data: pd.DataFrame,
    settings: dict,
) -> list[AgentRecommendation]:
    """Generate portfolio-level executive recommendations."""

    if optimisation_data.empty:
        return []

    thresholds = settings[
        "thresholds"
    ]["executive"]

    critical_count = int(
        (
            optimisation_data[
                "stockout_risk"
            ]
            == "Critical"
        ).sum()
    )

    high_count = int(
        (
            optimisation_data[
                "stockout_risk"
            ]
            == "High"
        ).sum()
    )

    procurement_value = float(
        optimisation_data[
            "procurement_value_usd"
        ].sum()
    )

    recommendations: list[
        AgentRecommendation
    ] = []

    if (
        critical_count
        >= int(
            thresholds[
                "critical_parts_trigger"
            ]
        )
    ):
        recommendations.append(
            AgentRecommendation(
                recommendation_id=(
                    create_recommendation_id(
                        agent_name=AGENT_NAME,
                        recommendation_type=(
                            "Critical Stock Exposure"
                        ),
                        part_number=None,
                        sequence=1,
                    )
                ),
                agent_name=AGENT_NAME,
                target_role=TARGET_ROLE,
                recommendation_type=(
                    "Critical Stock Exposure"
                ),
                priority="Critical",
                part_number=None,
                title=(
                    "Management action required for "
                    "critical stock exposure"
                ),
                recommendation=(
                    "Convene a cross-functional review covering "
                    "Procurement, Engineering, Operations, Finance "
                    "and Quality for all critical stock risks."
                ),
                rationale=(
                    f"{critical_count} forecast-active parts are "
                    f"classified as Critical stockout risk."
                ),
                forecast_confidence=None,
                evidence=[
                    evidence(
                        "critical_part_count",
                        critical_count,
                        "inventory_optimisation_results",
                    )
                ],
                human_approval_required=True,
                automatic_action_allowed=False,
                status="Pending accountable manager review",
            )
        )

    if (
        high_count
        >= int(
            thresholds[
                "high_risk_parts_trigger"
            ]
        )
    ):
        recommendations.append(
            AgentRecommendation(
                recommendation_id=(
                    create_recommendation_id(
                        agent_name=AGENT_NAME,
                        recommendation_type=(
                            "High-Risk Portfolio"
                        ),
                        part_number=None,
                        sequence=2,
                    )
                ),
                agent_name=AGENT_NAME,
                target_role=TARGET_ROLE,
                recommendation_type=(
                    "High-Risk Portfolio"
                ),
                priority="High",
                part_number=None,
                title=(
                    "Review high-risk spare-parts portfolio"
                ),
                recommendation=(
                    "Approve a coordinated recovery plan with "
                    "priorities, funding limits, accountable owners "
                    "and completion dates."
                ),
                rationale=(
                    f"{high_count} forecast-active parts are "
                    f"classified as High stockout risk."
                ),
                forecast_confidence=None,
                evidence=[
                    evidence(
                        "high_risk_part_count",
                        high_count,
                        "inventory_optimisation_results",
                    )
                ],
                human_approval_required=True,
                automatic_action_allowed=False,
                status="Pending accountable manager review",
            )
        )

    if procurement_value >= float(
        thresholds[
            "procurement_value_trigger_usd"
        ]
    ):
        recommendations.append(
            AgentRecommendation(
                recommendation_id=(
                    create_recommendation_id(
                        agent_name=AGENT_NAME,
                        recommendation_type=(
                            "Procurement Funding Exposure"
                        ),
                        part_number=None,
                        sequence=3,
                    )
                ),
                agent_name=AGENT_NAME,
                target_role=TARGET_ROLE,
                recommendation_type=(
                    "Procurement Funding Exposure"
                ),
                priority="High",
                part_number=None,
                title=(
                    "Review projected procurement funding exposure"
                ),
                recommendation=(
                    "Confirm that procurement priorities are aligned "
                    "with operational risk, technical criticality and "
                    "the approved financial plan."
                ),
                rationale=(
                    f"Projected procurement value is "
                    f"USD {procurement_value:,.2f}."
                ),
                forecast_confidence=None,
                evidence=[
                    evidence(
                        "total_procurement_value_usd",
                        procurement_value,
                        "inventory_optimisation_results",
                    )
                ],
                human_approval_required=True,
                automatic_action_allowed=False,
                status="Pending accountable manager review",
            )
        )

    return recommendations