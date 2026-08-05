"""Quality and governance advisory agent."""

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


AGENT_NAME = "Quality Agent"
TARGET_ROLE = "Quality Manager"


def generate_quality_recommendations(
    optimisation_data: pd.DataFrame,
    settings: dict,
) -> list[AgentRecommendation]:
    """Generate quality and governance recommendations."""

    if optimisation_data.empty:
        return []

    recommendations: list[
        AgentRecommendation
    ] = []

    review_rows = optimisation_data.loc[
        (
            optimisation_data[
                "recommended_order_quantity"
            ]
            > 0
        )
        & (
            (
                optimisation_data[
                    "forecast_confidence"
                ]
                == "Low"
            )
            | (
                optimisation_data[
                    "stockout_risk"
                ]
                .isin(
                    [
                        "Critical",
                        "High",
                    ]
                )
            )
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

    for sequence, row in enumerate(
        review_rows.itertuples(index=False),
        start=1,
    ):
        part_number = safe_text(
            row.part_number
        )

        recommendations.append(
            AgentRecommendation(
                recommendation_id=(
                    create_recommendation_id(
                        agent_name=AGENT_NAME,
                        recommendation_type=(
                            "Quality and Traceability Review"
                        ),
                        part_number=part_number,
                        sequence=sequence,
                    )
                ),
                agent_name=AGENT_NAME,
                target_role=TARGET_ROLE,
                recommendation_type=(
                    "Quality and Traceability Review"
                ),
                priority=(
                    "High"
                    if safe_text(
                        row.stockout_risk
                    )
                    in {
                        "Critical",
                        "High",
                    }
                    else "Medium"
                ),
                part_number=part_number,
                title=(
                    f"Quality review before order: "
                    f"{part_number}"
                ),
                recommendation=(
                    "Confirm approved supplier status, required "
                    "certification, traceability, shelf-life controls, "
                    "airworthiness documentation and independent "
                    "authorisation before procurement."
                ),
                rationale=(
                    f"Stockout risk is "
                    f"{safe_text(row.stockout_risk)} and forecast "
                    f"confidence is "
                    f"{safe_text(row.forecast_confidence)}."
                ),
                forecast_confidence=safe_text(
                    row.forecast_confidence
                ),
                evidence=[
                    evidence(
                        "stockout_risk",
                        safe_text(
                            row.stockout_risk
                        ),
                        "inventory_optimisation_results",
                    ),
                    evidence(
                        "forecast_confidence",
                        safe_text(
                            row.forecast_confidence
                        ),
                        "inventory_optimisation_results",
                    ),
                    evidence(
                        "procurement_value_usd",
                        safe_float(
                            row.procurement_value_usd
                        ),
                        "inventory_optimisation_results",
                    ),
                    evidence(
                        "human_approval_required",
                        bool(
                            row.human_approval_required
                        ),
                        "inventory_optimisation_results",
                    ),
                ],
                human_approval_required=True,
                automatic_action_allowed=False,
                status="Pending quality review",
            )
        )

    return recommendations