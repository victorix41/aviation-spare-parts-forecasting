"""Human management decision audit controls."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.audit.decision_audit import (
    DecisionAuditError,
    DecisionAuditRepository,
)
from src.dashboards.data_access import (
    DashboardRepository,
)


def render_decision_audit(
    *,
    repository: DashboardRepository,
    audit_database_path: Path,
    part_number: str,
    settings: dict,
) -> None:
    """Render human management-decision audit controls."""

    audit_settings = (
        settings.get(
            "decision_audit",
            {},
        )
    )

    if not bool(
        audit_settings.get(
            "enabled",
            True,
        )
    ):
        return

    st.markdown(
        "### Management Decision Audit Trail"
    )

    recommendations = (
        repository
        .load_part_recommendation_traces(
            part_number
        )
    )

    if recommendations.empty:
        st.info(
            "No agent recommendations are available "
            "for management decision recording."
        )
        return

    options: dict[str, str] = {}

    for row in recommendations.itertuples(
        index=False
    ):
        label = (
            f"{row.agent_name} — "
            f"{row.priority} — "
            f"{row.recommendation_id}"
        )

        options[label] = (
            row.recommendation_id
        )

    selected_label = st.selectbox(
        "Select recommendation for management decision",
        options=list(
            options.keys()
        ),
        key=f"decision_audit_recommendation_{part_number}",
    )

    recommendation_id = options[
        selected_label
    ]

    recommendation = (
        repository
        .load_recommendation_trace(
            recommendation_id
        )
    )

    if not recommendation:
        st.warning(
            "The selected recommendation "
            "could not be loaded."
        )
        return

    summary_columns = st.columns(4)

    summary_columns[0].metric(
        "Recommendation ID",
        recommendation_id,
    )

    summary_columns[1].metric(
        "Assurance",
        str(
            recommendation.get(
                "assurance_status"
            )
            or "Unavailable"
        ),
    )

    summary_columns[2].metric(
        "Priority",
        str(
            recommendation.get(
                "priority"
            )
            or "Unavailable"
        ),
    )

    summary_columns[3].metric(
        "Automatic action",
        "Allowed"
        if recommendation.get(
            "automatic_action_allowed"
        )
        else "Not allowed",
    )

    st.markdown(
        "**Recommendation under review**"
    )

    st.write(
        recommendation.get(
            "recommendation"
        )
        or "Unavailable"
    )

    allowed_decisions = (
        audit_settings.get(
            "allowed_decisions",
            [
                "Accepted",
                "Deferred",
                "Rejected",
            ],
        )
    )

    decision = st.radio(
        "Management decision",
        options=allowed_decisions,
        horizontal=True,
        key=f"management_decision_{recommendation_id}",
    )

    decision_reason = st.text_area(
        "Decision reason",
        placeholder=(
            "Record the management basis "
            "for this decision."
        ),
        key=f"decision_reason_{recommendation_id}",
    )

    reviewer_reference = st.text_input(
        "Reviewer reference",
        placeholder=(
            "Optional name, initials, role or "
            "internal review reference."
        ),
        key=f"reviewer_reference_{recommendation_id}",
    )

    st.info(
        "Recording this decision creates an audit "
        "record only. It does not create a purchase "
        "order, update inventory, approve expenditure "
        "or trigger an operational action."
    )

    if st.button(
        "Record Management Decision",
        type="primary",
        key=f"record_decision_{recommendation_id}",
    ):
        require_reason = bool(
            audit_settings.get(
                "require_decision_reason",
                True,
            )
        )

        if (
            require_reason
            and not decision_reason.strip()
        ):
            st.error(
                "A decision reason is required."
            )
            return

        audit_repository = (
            DecisionAuditRepository(
                audit_database_path
            )
        )

        try:
            audit_id = (
                audit_repository
                .record_decision(
                    recommendation=recommendation,
                    management_decision=decision,
                    decision_reason=decision_reason,
                    reviewer_reference=(
                        reviewer_reference.strip()
                        or None
                    ),
                )
            )

        except DecisionAuditError as exc:
            st.error(
                f"Management decision was not recorded: {exc}"
            )
            return

        st.success(
            "Management decision recorded successfully. "
            f"Audit ID: {audit_id}"
        )

    st.markdown(
        "**Recorded decision history**"
    )

    audit_repository = (
        DecisionAuditRepository(
            audit_database_path
        )
    )

    history = (
        audit_repository
        .load_history(
            part_number=part_number
        )
    )

    if history.empty:
        st.caption(
            "No management decisions have yet "
            "been recorded for this spare part."
        )
    else:
        st.dataframe(
            history,
            width="stretch",
            hide_index=True,
        )