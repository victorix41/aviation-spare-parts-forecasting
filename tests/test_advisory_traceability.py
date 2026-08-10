"""Tests for deterministic advisory traceability."""

from src.agents.traceability import (
    build_advisory_trace,
    determine_traceability_status,
)


def test_complete_trace_is_traceable() -> None:
    """A complete approved advisory should be traceable."""

    trace = build_advisory_trace(
        {
            "recommendation_id": "REC-001",
            "agent_name": "Procurement Agent",
            "target_role": "Procurement Manager",
            "recommendation_type": "Procurement Review",
            "priority": "High",
            "part_number": "PN-001",
            "title": "Review procurement",
            "recommendation": "Review order quantity.",
            "rationale": "High stockout risk.",
            "forecast_confidence": "Medium",
            "evidence": "Stored analytical evidence.",
            "human_approval_required": True,
            "automatic_action_allowed": False,
            "status": "Pending review",
            "assurance_status": "Passed",
            "approved_for_management_display": True,
        }
    )

    assert (
        determine_traceability_status(
            trace
        )
        == "Traceable"
    )


def test_missing_evidence_is_incomplete() -> None:
    """An advisory without evidence should be incomplete."""

    trace = build_advisory_trace(
        {
            "recommendation_id": "REC-001",
            "agent_name": "Quality Agent",
            "target_role": "Quality Manager",
            "recommendation": "Review.",
            "rationale": "Reason.",
            "evidence": "",
            "assurance_status": "Passed",
            "approved_for_management_display": True,
        }
    )

    assert (
        determine_traceability_status(
            trace
        )
        == "Incomplete"
    )


def test_unapproved_trace_is_restricted() -> None:
    """A complete but undisplayable advisory should be restricted."""

    trace = build_advisory_trace(
        {
            "recommendation_id": "REC-001",
            "agent_name": "Finance Agent",
            "target_role": "Finance Manager",
            "recommendation": "Review.",
            "rationale": "Reason.",
            "evidence": "Evidence.",
            "assurance_status": "Passed",
            "approved_for_management_display": False,
        }
    )

    assert (
        determine_traceability_status(
            trace
        )
        == "Restricted"
    )

def test_trace_preserves_assurance_status() -> None:
    """The trace should preserve stored assurance status."""

    trace = build_advisory_trace(
        {
            "recommendation_id": "REC-001",
            "agent_name": "Procurement Agent",
            "target_role": "Procurement Manager",
            "recommendation": "Review order.",
            "rationale": "High stockout risk.",
            "evidence": "Stored evidence.",
            "assurance_status": "Passed",
            "approved_for_management_display": True,
        }
    )

    assert (
        trace["assurance_status"]
        == "Passed"
    )


def test_trace_requires_assurance_status() -> None:
    """Missing assurance status should make trace incomplete."""

    trace = build_advisory_trace(
        {
            "recommendation_id": "REC-001",
            "agent_name": "Quality Agent",
            "target_role": "Quality Manager",
            "recommendation": "Review.",
            "rationale": "Quality review required.",
            "evidence": "Evidence.",
            "approved_for_management_display": True,
        }
    )

    assert (
        determine_traceability_status(
            trace
        )
        == "Incomplete"
    )