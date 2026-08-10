"""Deterministic advisory traceability utilities."""

from __future__ import annotations

from typing import Any


def build_advisory_trace(
    recommendation: dict[str, Any],
) -> dict[str, Any]:
    """Build an auditable advisory trace from stored fields."""

    return {
        "recommendation_id": recommendation.get(
            "recommendation_id"
        ),
        "agent_name": recommendation.get(
            "agent_name"
        ),
        "target_role": recommendation.get(
            "target_role"
        ),
        "recommendation_type": recommendation.get(
            "recommendation_type"
        ),
        "priority": recommendation.get(
            "priority"
        ),
        "part_number": recommendation.get(
            "part_number"
        ),
        "title": recommendation.get(
            "title"
        ),
        "recommendation": recommendation.get(
            "recommendation"
        ),
        "rationale": recommendation.get(
            "rationale"
        ),
        "forecast_confidence": recommendation.get(
            "forecast_confidence"
        ),
        "evidence": recommendation.get(
            "evidence"
        ),
        "human_approval_required": recommendation.get(
            "human_approval_required"
        ),
        "automatic_action_allowed": recommendation.get(
            "automatic_action_allowed"
        ),
        "status": recommendation.get(
            "status"
        ),
        "assurance_status": recommendation.get(
            "assurance_status"
        ),
        "approved_for_management_display": recommendation.get(
            "approved_for_management_display"
        ),
    }


def determine_traceability_status(
    trace: dict[str, Any],
) -> str:
    """Determine whether an advisory is fully traceable."""

    required_fields = [
        "recommendation_id",
        "agent_name",
        "target_role",
        "recommendation",
        "rationale",
        "evidence",
        "assurance_status",
    ]

    for field in required_fields:
        value = trace.get(field)

        if value is None:
            return "Incomplete"

        if isinstance(value, str) and not value.strip():
            return "Incomplete"

    if (
        trace.get(
            "approved_for_management_display"
        )
        is not True
    ):
        return "Restricted"

    return "Traceable"