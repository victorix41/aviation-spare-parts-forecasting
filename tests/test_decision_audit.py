"""Tests for management decision auditing."""

from pathlib import Path

import pytest

from src.audit.decision_audit import (
    DecisionAuditError,
    DecisionAuditRepository,
)


def _recommendation() -> dict:
    """Return one test recommendation."""

    return {
        "recommendation_id": "REC-TEST-001",
        "part_number": "PN-001",
        "agent_name": "Operations Agent",
        "target_role": "Operations Manager",
        "recommendation_type": (
            "Maintenance Readiness"
        ),
        "priority": "Critical",
        "assurance_status": "Passed",
        "forecast_confidence": "Medium",
        "human_approval_required": True,
        "automatic_action_allowed": False,
        "status": "Pending review",
    }


def test_record_management_decision(
    tmp_path: Path,
) -> None:
    """A human decision should be appended."""

    repository = DecisionAuditRepository(
        tmp_path
        / "management_audit.duckdb"
    )

    audit_id = repository.record_decision(
        recommendation=_recommendation(),
        management_decision="Accepted",
        decision_reason=(
            "Reviewed and accepted "
            "for management planning."
        ),
        reviewer_reference="Test reviewer",
    )

    assert audit_id.startswith(
        "AUD-"
    )

    history = repository.load_history(
        recommendation_id=(
            "REC-TEST-001"
        )
    )

    assert len(history) == 1

    assert (
        history.iloc[0][
            "management_decision"
        ]
        == "Accepted"
    )


def test_decision_reason_is_required(
    tmp_path: Path,
) -> None:
    """Blank decision reasons must fail."""

    repository = DecisionAuditRepository(
        tmp_path
        / "management_audit.duckdb"
    )

    with pytest.raises(
        DecisionAuditError
    ):
        repository.record_decision(
            recommendation=(
                _recommendation()
            ),
            management_decision="Deferred",
            decision_reason="",
        )


def test_unsupported_decision_is_rejected(
    tmp_path: Path,
) -> None:
    """Only controlled management decisions are allowed."""

    repository = DecisionAuditRepository(
        tmp_path
        / "management_audit.duckdb"
    )

    with pytest.raises(
        DecisionAuditError
    ):
        repository.record_decision(
            recommendation=(
                _recommendation()
            ),
            management_decision=(
                "Automatically Approved"
            ),
            decision_reason="Test",
        )


def test_audit_does_not_enable_automatic_action(
    tmp_path: Path,
) -> None:
    """Audit logging must preserve automatic-action status."""

    repository = DecisionAuditRepository(
        tmp_path
        / "management_audit.duckdb"
    )

    repository.record_decision(
        recommendation=(
            _recommendation()
        ),
        management_decision="Accepted",
        decision_reason=(
            "Management planning review."
        ),
    )

    history = repository.load_history()

    assert (
        bool(
            history.iloc[0][
                "automatic_action_allowed"
            ]
        )
        is False
    )