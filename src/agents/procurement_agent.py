"""Procurement advisory agent."""

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


AGENT_NAME = "Procurement Agent"
TARGET_ROLE = "Procurement Manager"


def generate_procurement_recommendations(
    procurement_data: pd.DataFrame,
    settings: dict,
) -> list[AgentRecommendation]:
    """Generate procurement recommendations from approved analytics."""

    if procurement_data.empty:
        return []

    required_columns = {
        "part_number",
        "description",
        "stockout_risk",
        "procurement_priority",
        "recommended_order_quantity",
        "procurement_value_usd",
        "average_lead_time_days",
        "forecast_confidence",
        "recommendation_reason",
    }

    missing = sorted(
        required_columns.difference(
            procurement_data.columns
        )
    )

    if missing:
        raise ValueError(
            "Procurement data is missing columns: "
            + ", ".join(missing)
        )

    urgent_priority = int(
        settings["thresholds"][
            "procurement"
        ]["urgent_priority_maximum"]
    )

    high_value_threshold = float(
        settings["thresholds"][
            "procurement"
        ]["high_value_order_usd"]
    )

    long_lead_threshold = float(
        settings["thresholds"][
            "procurement"
        ]["long_lead_time_days"]
    )

    recommendations: list[
        AgentRecommendation
    ] = []

    ordered = procurement_data.sort_values(
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
        ordered.itertuples(index=False),
        start=1,
    ):
        part_number = safe_text(
            row.part_number
        )

        risk = safe_text(
            row.stockout_risk
        )

        priority_number = int(
            row.procurement_priority
        )

        procurement_value = safe_float(
            row.procurement_value_usd
        )

        lead_time = safe_float(
            row.average_lead_time_days
        )

        order_quantity = safe_float(
            row.recommended_order_quantity
        )

        if risk == "Critical":
            recommendation_priority = (
                "Critical"
            )
        elif priority_number <= urgent_priority:
            recommendation_priority = "High"
        elif procurement_value >= high_value_threshold:
            recommendation_priority = "Medium"
        else:
            recommendation_priority = "Low"

        concerns: list[str] = []

        if lead_time >= long_lead_threshold:
            concerns.append(
                "long procurement lead time"
            )

        if procurement_value >= high_value_threshold:
            concerns.append(
                "high procurement value"
            )

        concern_text = (
            ", ".join(concerns)
            if concerns
            else "standard procurement review"
        )

        recommendation = (
            f"Review procurement of "
            f"{order_quantity:.0f} units for "
            f"{part_number}. Validate supplier "
            f"availability, minimum order quantity, "
            f"approved sources and delivery commitment "
            f"before raising a purchase order."
        )

        rationale = (
            f"{safe_text(row.recommendation_reason)} "
            f"Additional considerations: {concern_text}."
        )

        recommendations.append(
            AgentRecommendation(
                recommendation_id=(
                    create_recommendation_id(
                        agent_name=AGENT_NAME,
                        recommendation_type=(
                            "Procurement Review"
                        ),
                        part_number=part_number,
                        sequence=sequence,
                    )
                ),
                agent_name=AGENT_NAME,
                target_role=TARGET_ROLE,
                recommendation_type=(
                    "Procurement Review"
                ),
                priority=recommendation_priority,
                part_number=part_number,
                title=(
                    f"Procurement review: "
                    f"{part_number}"
                ),
                recommendation=recommendation,
                rationale=rationale,
                forecast_confidence=safe_text(
                    row.forecast_confidence
                ),
                evidence=[
                    evidence(
                        "stockout_risk",
                        risk,
                        "procurement_recommendations",
                    ),
                    evidence(
                        "recommended_order_quantity",
                        order_quantity,
                        "procurement_recommendations",
                    ),
                    evidence(
                        "procurement_value_usd",
                        procurement_value,
                        "procurement_recommendations",
                    ),
                    evidence(
                        "average_lead_time_days",
                        lead_time,
                        "inventory_optimisation_results",
                    ),
                ],
                human_approval_required=True,
                automatic_action_allowed=False,
                status="Pending management review",
            )
        )

    return recommendations