"""Finance advisory agent."""

from __future__ import annotations

import pandas as pd

from src.agents.advisory_models import (
    AgentRecommendation,
)
from src.agents.advisory_utils import (
    create_recommendation_id,
    evidence,
    safe_float,
    safe_text,
)


AGENT_NAME = "Finance Agent"
TARGET_ROLE = "Finance Manager"


def generate_finance_recommendations(
    optimisation_data: pd.DataFrame,
    settings: dict,
) -> list[AgentRecommendation]:
    """Generate portfolio and part-level finance recommendations."""

    if optimisation_data.empty:
        return []

    thresholds = settings[
        "thresholds"
    ]["finance"]

    high_total = float(
        thresholds[
            "high_total_procurement_value_usd"
        ]
    )

    high_single = float(
        thresholds[
            "high_single_part_value_usd"
        ]
    )

    low_confidence_review = float(
        thresholds[
            "low_confidence_value_review_usd"
        ]
    )

    recommendations: list[
        AgentRecommendation
    ] = []

    total_procurement = float(
        optimisation_data[
            "procurement_value_usd"
        ].sum()
    )

    total_inventory = float(
        optimisation_data[
            "inventory_value_usd"
        ].sum()
    )

    priority = (
        "High"
        if total_procurement >= high_total
        else "Medium"
    )

    recommendations.append(
        AgentRecommendation(
            recommendation_id=(
                create_recommendation_id(
                    agent_name=AGENT_NAME,
                    recommendation_type=(
                        "Portfolio Budget Review"
                    ),
                    part_number=None,
                    sequence=1,
                )
            ),
            agent_name=AGENT_NAME,
            target_role=TARGET_ROLE,
            recommendation_type=(
                "Portfolio Budget Review"
            ),
            priority=priority,
            part_number=None,
            title=(
                "Review projected spare-parts "
                "procurement exposure"
            ),
            recommendation=(
                "Validate the projected procurement "
                "requirement against the approved budget, "
                "cash-flow plan and working-capital limits."
            ),
            rationale=(
                f"Projected procurement value is "
                f"USD {total_procurement:,.2f}, compared "
                f"with current analysed inventory value of "
                f"USD {total_inventory:,.2f}."
            ),
            forecast_confidence=None,
            evidence=[
                evidence(
                    "total_procurement_value_usd",
                    total_procurement,
                    "inventory_optimisation_results",
                ),
                evidence(
                    "total_inventory_value_usd",
                    total_inventory,
                    "inventory_optimisation_results",
                ),
            ],
            human_approval_required=True,
            automatic_action_allowed=False,
            status="Pending finance review",
        )
    )

    high_value_rows = optimisation_data.loc[
        optimisation_data[
            "procurement_value_usd"
        ]
        >= high_single
    ].sort_values(
        "procurement_value_usd",
        ascending=False,
    )

    for sequence, row in enumerate(
        high_value_rows.itertuples(index=False),
        start=2,
    ):
        procurement_value = safe_float(
            row.procurement_value_usd
        )

        confidence = safe_text(
            row.forecast_confidence
        )

        requires_extra_review = (
            confidence == "Low"
            and procurement_value
            >= low_confidence_review
        )

        recommendation = (
            "Perform an individual financial and "
            "commercial review before committing funds."
        )

        if requires_extra_review:
            recommendation += (
                " Forecast confidence is low, so use "
                "scenario analysis and management contingency."
            )

        recommendations.append(
            AgentRecommendation(
                recommendation_id=(
                    create_recommendation_id(
                        agent_name=AGENT_NAME,
                        recommendation_type=(
                            "High-Value Part Review"
                        ),
                        part_number=safe_text(
                            row.part_number
                        ),
                        sequence=sequence,
                    )
                ),
                agent_name=AGENT_NAME,
                target_role=TARGET_ROLE,
                recommendation_type=(
                    "High-Value Part Review"
                ),
                priority=(
                    "High"
                    if requires_extra_review
                    else "Medium"
                ),
                part_number=safe_text(
                    row.part_number
                ),
                title=(
                    "High-value procurement review: "
                    f"{safe_text(row.part_number)}"
                ),
                recommendation=recommendation,
                rationale=(
                    f"Projected procurement exposure is "
                    f"USD {procurement_value:,.2f}; forecast "
                    f"confidence is {confidence}."
                ),
                forecast_confidence=confidence,
                evidence=[
                    evidence(
                        "procurement_value_usd",
                        procurement_value,
                        "inventory_optimisation_results",
                    ),
                    evidence(
                        "forecast_confidence",
                        confidence,
                        "final_part_forecasts",
                    ),
                    evidence(
                        "recommended_order_quantity",
                        safe_float(
                            row.recommended_order_quantity
                        ),
                        "inventory_optimisation_results",
                    ),
                ],
                human_approval_required=True,
                automatic_action_allowed=False,
                status="Pending finance review",
            )
        )

    return recommendations