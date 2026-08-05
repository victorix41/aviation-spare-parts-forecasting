"""Operations advisory agent."""

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


AGENT_NAME = "Operations Agent"
TARGET_ROLE = "Operations Manager"


def generate_operations_recommendations(
    optimisation_data: pd.DataFrame,
    settings: dict,
) -> list[AgentRecommendation]:
    """Generate maintenance-readiness recommendations."""

    if optimisation_data.empty:
        return []

    thresholds = settings[
        "thresholds"
    ]["operations"]

    immediate = float(
        thresholds[
            "immediate_stockout_months"
        ]
    )

    near_term = float(
        thresholds[
            "near_term_stockout_months"
        ]
    )

    recommendations: list[
        AgentRecommendation
    ] = []

    relevant = optimisation_data.loc[
        optimisation_data[
            "stockout_risk"
        ].isin(
            [
                "Critical",
                "High",
            ]
        )
    ].sort_values(
        [
            "procurement_priority",
            "estimated_stockout_months",
        ],
        ascending=[
            True,
            True,
        ],
        na_position="first",
    )

    for sequence, row in enumerate(
        relevant.itertuples(index=False),
        start=1,
    ):
        stockout_months = getattr(
            row,
            "estimated_stockout_months",
            None,
        )

        stockout_months_value = (
            safe_float(stockout_months)
            if stockout_months is not None
            else 0.0
        )

        if stockout_months_value <= immediate:
            priority = "Critical"
            timing = "immediate"
        elif stockout_months_value <= near_term:
            priority = "High"
            timing = "near-term"
        else:
            priority = "Medium"
            timing = "planned"

        part_number = safe_text(
            row.part_number
        )

        recommendations.append(
            AgentRecommendation(
                recommendation_id=(
                    create_recommendation_id(
                        agent_name=AGENT_NAME,
                        recommendation_type=(
                            "Maintenance Readiness"
                        ),
                        part_number=part_number,
                        sequence=sequence,
                    )
                ),
                agent_name=AGENT_NAME,
                target_role=TARGET_ROLE,
                recommendation_type=(
                    "Maintenance Readiness"
                ),
                priority=priority,
                part_number=part_number,
                title=(
                    f"{timing.title()} stock risk: "
                    f"{part_number}"
                ),
                recommendation=(
                    "Review upcoming maintenance requirements, "
                    "repair-order priorities, available substitutes "
                    "and operational contingency actions."
                ),
                rationale=(
                    f"Estimated stock cover is "
                    f"{stockout_months_value:.2f} months and the "
                    f"stockout risk is {safe_text(row.stockout_risk)}."
                ),
                forecast_confidence=safe_text(
                    row.forecast_confidence
                ),
                evidence=[
                    evidence(
                        "estimated_stockout_months",
                        stockout_months_value,
                        "inventory_optimisation_results",
                    ),
                    evidence(
                        "stockout_risk",
                        safe_text(
                            row.stockout_risk
                        ),
                        "inventory_optimisation_results",
                    ),
                    evidence(
                        "current_balance",
                        safe_float(
                            row.current_balance
                        ),
                        "inventory_optimisation_results",
                    ),
                    evidence(
                        "reorder_point",
                        safe_float(
                            row.reorder_point
                        ),
                        "inventory_optimisation_results",
                    ),
                ],
                human_approval_required=True,
                automatic_action_allowed=False,
                status="Pending operations review",
            )
        )

    return recommendations