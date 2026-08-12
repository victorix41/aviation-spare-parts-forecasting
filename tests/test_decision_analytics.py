"""Tests for management decision audit analytics."""

import pandas as pd

from src.audit.decision_analytics import (
    decision_breakdown,
    filter_decision_history,
    priority_breakdown,
    role_breakdown,
    summarise_decisions,
)


def _history() -> pd.DataFrame:
    """Return deterministic audit history."""

    return pd.DataFrame(
        [
            {
                "recommendation_id": "REC-001",
                "part_number": "PN-001",
                "target_role": "Operations Manager",
                "priority": "Critical",
                "management_decision": "Accepted",
            },
            {
                "recommendation_id": "REC-002",
                "part_number": "PN-002",
                "target_role": "Finance Manager",
                "priority": "High",
                "management_decision": "Deferred",
            },
            {
                "recommendation_id": "REC-003",
                "part_number": "PN-001",
                "target_role": "Operations Manager",
                "priority": "High",
                "management_decision": "Rejected",
            },
        ]
    )


def test_decision_summary() -> None:
    """Summary counts should be deterministic."""

    summary = summarise_decisions(
        _history()
    )

    assert summary[
        "total_decisions"
    ] == 3

    assert summary[
        "accepted"
    ] == 1

    assert summary[
        "deferred"
    ] == 1

    assert summary[
        "rejected"
    ] == 1

    assert summary[
        "unique_parts"
    ] == 2


def test_decision_breakdown() -> None:
    """All controlled decisions should be counted."""

    result = decision_breakdown(
        _history()
    )

    assert (
        result[
            "decision_count"
        ].sum()
        == 3
    )


def test_role_breakdown() -> None:
    """Role breakdown should preserve all records."""

    result = role_breakdown(
        _history()
    )

    assert (
        result[
            "decision_count"
        ].sum()
        == 3
    )


def test_priority_breakdown() -> None:
    """Priority breakdown should preserve all records."""

    result = priority_breakdown(
        _history()
    )

    assert (
        result[
            "decision_count"
        ].sum()
        == 3
    )


def test_history_filtering() -> None:
    """Audit history should filter deterministically."""

    result = filter_decision_history(
        _history(),
        target_role=(
            "Operations Manager"
        ),
        decision="Accepted",
    )

    assert len(result) == 1

    assert (
        result.iloc[0][
            "recommendation_id"
        ]
        == "REC-001"
    )