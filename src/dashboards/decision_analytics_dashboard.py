"""Management decision audit analytics dashboard."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.audit.decision_analytics import (
    decision_breakdown,
    filter_decision_history,
    priority_breakdown,
    role_breakdown,
    summarise_decisions,
)
from src.audit.decision_audit import (
    DecisionAuditRepository,
)


def render_decision_analytics(
    *,
    audit_database_path: Path,
    settings: dict,
    target_role: str | None = None,
) -> None:
    """Render management decision audit analytics."""

    analytics_settings = (
        settings.get(
            "decision_analytics",
            {},
        )
    )

    if not bool(
        analytics_settings.get(
            "enabled",
            True,
        )
    ):
        return

    st.markdown(
        "### Management Decision Analytics"
    )

    audit_repository = (
        DecisionAuditRepository(
            audit_database_path
        )
    )

    history = (
        audit_repository
        .load_all_history()
    )

    if target_role is not None:
        history = filter_decision_history(
            history,
            target_role=target_role,
        )

    summary = summarise_decisions(
        history
    )

    metric_columns = st.columns(6)

    metric_columns[0].metric(
        "Total decisions",
        summary[
            "total_decisions"
        ],
    )

    metric_columns[1].metric(
        "Accepted",
        summary[
            "accepted"
        ],
    )

    metric_columns[2].metric(
        "Deferred",
        summary[
            "deferred"
        ],
    )

    metric_columns[3].metric(
        "Rejected",
        summary[
            "rejected"
        ],
    )

    metric_columns[4].metric(
        "Parts reviewed",
        summary[
            "unique_parts"
        ],
    )

    metric_columns[5].metric(
        "Recommendations reviewed",
        summary[
            "unique_recommendations"
        ],
    )

    if history.empty:
        st.info(
            "No management decisions have yet "
            "been recorded for this view."
        )
        return

    st.caption(
        "Accepted means accepted for management "
        "decision-support review only. It does not "
        "constitute procurement, expenditure, inventory "
        "or operational approval."
    )

    filter_columns = st.columns(2)

    decision_options = [
        "All",
        "Accepted",
        "Deferred",
        "Rejected",
    ]

    selected_decision = (
        filter_columns[0]
        .selectbox(
            "Management decision",
            options=decision_options,
            key=(
                "decision_analytics_decision_"
                + str(
                    target_role
                    or "all"
                )
            ),
        )
    )

    priority_options = [
        "All",
        "Critical",
        "High",
        "Medium",
        "Low",
    ]

    selected_priority = (
        filter_columns[1]
        .selectbox(
            "Recommendation priority",
            options=priority_options,
            key=(
                "decision_analytics_priority_"
                + str(
                    target_role
                    or "all"
                )
            ),
        )
    )

    filtered_history = (
        filter_decision_history(
            history,
            decision=(
                None
                if selected_decision == "All"
                else selected_decision
            ),
            priority=(
                None
                if selected_priority == "All"
                else selected_priority
            ),
        )
    )

    st.markdown(
        "**Decision Breakdown**"
    )

    st.dataframe(
        decision_breakdown(
            history
        ),
        width="stretch",
        hide_index=True,
    )

    if target_role is None:
        st.markdown(
            "**Decision Breakdown by Management Role**"
        )

        st.dataframe(
            role_breakdown(
                history
            ),
            width="stretch",
            hide_index=True,
        )

    st.markdown(
        "**Decision Breakdown by Priority**"
    )

    st.dataframe(
        priority_breakdown(
            history
        ),
        width="stretch",
        hide_index=True,
    )

    st.markdown(
        "**Recent Management Decisions**"
    )

    recent_limit = int(
        analytics_settings.get(
            "recent_decision_limit",
            25,
        )
    )

    recent_history = (
        filtered_history
        .head(
            recent_limit
        )
    )

    if recent_history.empty:
        st.info(
            "No management decisions match "
            "the selected filters."
        )
    else:
        display_columns = [
            "recorded_at",
            "audit_id",
            "recommendation_id",
            "part_number",
            "agent_name",
            "target_role",
            "priority",
            "assurance_status",
            "forecast_confidence",
            "management_decision",
            "decision_reason",
            "reviewer_reference",
            "automatic_action_allowed",
        ]

        available_columns = [
            column
            for column in display_columns
            if column
            in recent_history.columns
        ]

        st.dataframe(
            recent_history[
                available_columns
            ],
            width="stretch",
            hide_index=True,
        )

    st.caption(
        "Decision analytics are derived only from "
        "the append-only management audit database. "
        "No operational system is updated from this view."
    )