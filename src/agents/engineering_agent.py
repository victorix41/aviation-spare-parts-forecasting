"""Engineering advisory agent."""

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


AGENT_NAME = "Engineering Agent"
TARGET_ROLE = "Engineering Manager"


def generate_engineering_recommendations(
    optimisation_data: pd.DataFrame,
    settings: dict,
) -> list[AgentRecommendation]:
    """Generate engineering validation recommendations."""

    if optimisation_data.empty:
        return []

    criticality_levels = set(
        settings["thresholds"][
            "engineering"
        ]["criticality_levels"]
    )

    relevant = optimisation_data.loc[
        optimisation_data[
            "engineering_criticality"
        ].isin(criticality_levels)
        & (
            optimisation_data[
                "recommended_order_quantity"
            ]
            > 0
        )
    ].sort_values(
        [
            "procurement_priority",
            "procurement_value_usd",
        ],
        ascending=[
            True,
            False,
        ],
    )

    recommendations: list[
        AgentRecommendation
    ] = []

    for sequence, row in enumerate(
        relevant.itertuples(index=False),
        start=1,
    ):
        part_number = safe_text(
            row.part_number
        )

        criticality = safe_text(
            row.engineering_criticality
        )

        confidence = safe_text(
            row.forecast_confidence
        )

        recommendations.append(
            AgentRecommendation(
                recommendation_id=(
                    create_recommendation_id(
                        agent_name=AGENT_NAME,
                        recommendation_type=(
                            "Technical Requirement Validation"
                        ),
                        part_number=part_number,
                        sequence=sequence,
                    )
                ),
                agent_name=AGENT_NAME,
                target_role=TARGET_ROLE,
                recommendation_type=(
                    "Technical Requirement Validation"
                ),
                priority=(
                    "Critical"
                    if criticality == "Critical"
                    else "High"
                ),
                part_number=part_number,
                title=(
                    f"Engineering validation: "
                    f"{part_number}"
                ),
                recommendation=(
                    "Validate technical necessity, approved "
                    "alternates, interchangeability, repair-versus-"
                    "buy options and applicable maintenance demand "
                    "before procurement approval."
                ),
                rationale=(
                    f"The part is classified as {criticality} "
                    f"and has a recommended order quantity of "
                    f"{safe_float(row.recommended_order_quantity):.0f}. "
                    f"Forecast confidence is {confidence}."
                ),
                forecast_confidence=confidence,
                evidence=[
                    evidence(
                        "engineering_criticality",
                        criticality,
                        "inventory_optimisation_results",
                    ),
                    evidence(
                        "recommended_order_quantity",
                        safe_float(
                            row.recommended_order_quantity
                        ),
                        "inventory_optimisation_results",
                    ),
                    evidence(
                        "selected_forecast_model",
                        safe_text(
                            row.selected_forecast_model
                        ),
                        "inventory_optimisation_results",
                    ),
                    evidence(
                        "forecast_confidence",
                        confidence,
                        "inventory_optimisation_results",
                    ),
                ],
                human_approval_required=True,
                automatic_action_allowed=False,
                status="Pending engineering validation",
            )
        )

    return recommendations