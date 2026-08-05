"""Final assurance checks for agent recommendations."""

from __future__ import annotations

from src.agents.advisory_models import (
    AgentRecommendation,
    AssuranceFinding,
)


def assure_recommendation(
    recommendation: AgentRecommendation,
    settings: dict,
) -> AssuranceFinding:
    """Validate one recommendation before management display."""

    evidence_complete = bool(
        recommendation.evidence
    )

    governance_compliant = (
        recommendation.human_approval_required
        and not recommendation.automatic_action_allowed
    )

    messages: list[str] = []

    if not evidence_complete:
        messages.append(
            "Recommendation has no supporting evidence."
        )

    if not recommendation.human_approval_required:
        messages.append(
            "Human approval is not marked as required."
        )

    if recommendation.automatic_action_allowed:
        messages.append(
            "Automatic action is incorrectly permitted."
        )

    approved = (
        evidence_complete
        and governance_compliant
        and bool(recommendation.recommendation.strip())
        and bool(recommendation.rationale.strip())
    )

    return AssuranceFinding(
        recommendation_id=(
            recommendation.recommendation_id
        ),
        assurance_status=(
            "Passed"
            if approved
            else "Failed"
        ),
        finding_type=(
            "No exception"
            if approved
            else "Governance or evidence exception"
        ),
        finding_message=(
            "Recommendation passed final assurance."
            if approved
            else " ".join(messages)
        ),
        evidence_complete=evidence_complete,
        governance_compliant=governance_compliant,
        approved_for_management_display=approved,
    )


def run_final_assurance(
    recommendations: list[AgentRecommendation],
    settings: dict,
) -> list[AssuranceFinding]:
    """Run final assurance across all recommendations."""

    return [
        assure_recommendation(
            recommendation,
            settings,
        )
        for recommendation in recommendations
    ]