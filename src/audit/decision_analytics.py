"""Deterministic management decision audit analytics."""

from __future__ import annotations

from typing import Any

import pandas as pd


DECISION_ORDER = [
    "Accepted",
    "Deferred",
    "Rejected",
]


def summarise_decisions(
    history: pd.DataFrame,
) -> dict[str, int]:
    """Summarise management decision audit history."""

    if history.empty:
        return {
            "total_decisions": 0,
            "accepted": 0,
            "deferred": 0,
            "rejected": 0,
            "unique_parts": 0,
            "unique_recommendations": 0,
        }

    decisions = (
        history[
            "management_decision"
        ]
        .fillna("")
        .astype(str)
    )

    return {
        "total_decisions": len(
            history
        ),
        "accepted": int(
            (
                decisions
                == "Accepted"
            ).sum()
        ),
        "deferred": int(
            (
                decisions
                == "Deferred"
            ).sum()
        ),
        "rejected": int(
            (
                decisions
                == "Rejected"
            ).sum()
        ),
        "unique_parts": int(
            history[
                "part_number"
            ]
            .dropna()
            .nunique()
        ),
        "unique_recommendations": int(
            history[
                "recommendation_id"
            ]
            .dropna()
            .nunique()
        ),
    }


def decision_breakdown(
    history: pd.DataFrame,
) -> pd.DataFrame:
    """Return decision counts in controlled order."""

    if history.empty:
        return pd.DataFrame(
            columns=[
                "management_decision",
                "decision_count",
            ]
        )

    counts = (
        history[
            "management_decision"
        ]
        .value_counts(
            dropna=False
        )
        .rename_axis(
            "management_decision"
        )
        .reset_index(
            name="decision_count"
        )
    )

    order = {
        decision: index
        for index, decision in enumerate(
            DECISION_ORDER
        )
    }

    counts["_sort_order"] = (
        counts[
            "management_decision"
        ]
        .map(
            order
        )
        .fillna(
            99
        )
    )

    return (
        counts
        .sort_values(
            [
                "_sort_order",
                "management_decision",
            ]
        )
        .drop(
            columns=[
                "_sort_order",
            ]
        )
        .reset_index(
            drop=True
        )
    )


def role_breakdown(
    history: pd.DataFrame,
) -> pd.DataFrame:
    """Return management decisions by target role."""

    if history.empty:
        return pd.DataFrame(
            columns=[
                "target_role",
                "management_decision",
                "decision_count",
            ]
        )

    return (
        history
        .groupby(
            [
                "target_role",
                "management_decision",
            ],
            dropna=False,
        )
        .size()
        .reset_index(
            name="decision_count"
        )
        .sort_values(
            [
                "target_role",
                "management_decision",
            ]
        )
        .reset_index(
            drop=True
        )
    )


def priority_breakdown(
    history: pd.DataFrame,
) -> pd.DataFrame:
    """Return management decisions by recommendation priority."""

    if history.empty:
        return pd.DataFrame(
            columns=[
                "priority",
                "management_decision",
                "decision_count",
            ]
        )

    priority_order = {
        "Critical": 1,
        "High": 2,
        "Medium": 3,
        "Low": 4,
    }

    result = (
        history
        .groupby(
            [
                "priority",
                "management_decision",
            ],
            dropna=False,
        )
        .size()
        .reset_index(
            name="decision_count"
        )
    )

    result["_priority_order"] = (
        result[
            "priority"
        ]
        .map(
            priority_order
        )
        .fillna(
            99
        )
    )

    return (
        result
        .sort_values(
            [
                "_priority_order",
                "priority",
                "management_decision",
            ]
        )
        .drop(
            columns=[
                "_priority_order",
            ]
        )
        .reset_index(
            drop=True
        )
    )


def filter_decision_history(
    history: pd.DataFrame,
    *,
    target_role: str | None = None,
    decision: str | None = None,
    priority: str | None = None,
) -> pd.DataFrame:
    """Filter audit history without modifying source data."""

    filtered = history.copy()

    if target_role:
        filtered = filtered[
            filtered[
                "target_role"
            ]
            == target_role
        ]

    if decision:
        filtered = filtered[
            filtered[
                "management_decision"
            ]
            == decision
        ]

    if priority:
        filtered = filtered[
            filtered[
                "priority"
            ]
            == priority
        ]

    return filtered.reset_index(
        drop=True
    )