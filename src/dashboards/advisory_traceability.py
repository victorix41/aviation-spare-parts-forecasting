"""Reusable agent advisory traceability dashboard."""

from __future__ import annotations

import streamlit as st

from src.agents.traceability import (
    build_advisory_trace,
    determine_traceability_status,
)
from src.dashboards.data_access import (
    DashboardRepository,
)


def render_advisory_traceability(
    *,
    repository: DashboardRepository,
    part_number: str,
) -> None:
    """Render auditable agent recommendation traceability."""

    st.markdown(
        "### Agent Advisory Traceability"
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
            "for this spare part."
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
        "Select recommendation for trace review",
        options=list(
            options.keys()
        ),
        key=f"traceability_{part_number}",
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

    trace = build_advisory_trace(
        recommendation
    )

    traceability_status = (
        determine_traceability_status(
            trace
        )
    )

    metric_columns = st.columns(5)

    metric_columns[0].metric(
        "Traceability",
        traceability_status,
    )

    metric_columns[1].metric(
        "Agent",
        str(
            trace.get(
                "agent_name"
            )
            or "Unavailable"
        ),
    )

    metric_columns[2].metric(
        "Target role",
        str(
            trace.get(
                "target_role"
            )
            or "Unavailable"
        ),
    )

    metric_columns[3].metric(
        "Priority",
        str(
            trace.get(
                "priority"
            )
            or "Unavailable"
        ),
    )

    metric_columns[4].metric(
        "Assurance",
        str(
            trace.get(
                "assurance_status"
            )
            or "Unavailable"
        ),
    )

    st.caption(
        "Recommendation ID: "
        f"{recommendation_id}"
    )

    st.markdown(
        "**Recommendation**"
    )

    st.write(
        trace.get(
            "recommendation"
        )
        or "Unavailable"
    )

    st.markdown(
        "**Rationale**"
    )

    st.write(
        trace.get(
            "rationale"
        )
        or "Unavailable"
    )

    st.markdown(
        "**Supporting evidence**"
    )

    st.code(
        str(
            trace.get(
                "evidence"
            )
            or "Unavailable"
        ),
        language="text",
    )

    governance_columns = st.columns(3)

    governance_columns[0].metric(
        "Human approval required",
        "Yes"
        if trace.get(
            "human_approval_required"
        )
        else "No",
    )

    governance_columns[1].metric(
        "Automatic action allowed",
        "Yes"
        if trace.get(
            "automatic_action_allowed"
        )
        else "No",
    )

    governance_columns[2].metric(
        "Management display approved",
        "Yes"
        if trace.get(
            "approved_for_management_display"
        )
        else "No",
    )

    st.markdown(
    "**Assurance Findings**"
)

    assurance_findings = (
        repository
        .load_recommendation_assurance_findings(
            recommendation_id
        )
    )

    if assurance_findings.empty:
        st.warning(
            "No detailed assurance finding "
            "is available for this recommendation."
        )

    else:
        for finding in assurance_findings.itertuples(
            index=False
        ):
            finding_status = str(
                finding.assurance_status
                or "Unavailable"
            )

            finding_type = str(
                finding.finding_type
                or "Assurance Review"
            )

            finding_message = str(
                finding.finding_message
                or "No finding message available."
            )

            evidence_complete = (
                "Yes"
                if finding.evidence_complete
                else "No"
            )

            governance_compliant = (
                "Yes"
                if finding.governance_compliant
                else "No"
            )

            management_display = (
                "Yes"
                if finding.approved_for_management_display
                else "No"
            )

            st.markdown(
                f"**{finding_type} — {finding_status}**"
            )

            st.write(
                finding_message
            )

            assurance_columns = st.columns(3)

            assurance_columns[0].metric(
                "Evidence complete",
                evidence_complete,
            )

            assurance_columns[1].metric(
                "Governance compliant",
                governance_compliant,
            )

            assurance_columns[2].metric(
                "Approved for display",
                management_display,
            )

    if traceability_status == "Traceable":
        st.success(
            "This recommendation has a complete "
            "stored evidence and assurance trail."
        )

    elif traceability_status == "Restricted":
        st.warning(
            "This recommendation is not approved "
            "for management display."
        )

    else:
        st.error(
            "The advisory trace is incomplete. "
            "Review the underlying recommendation record."
        )

    st.caption(
        "This view provides traceability only. "
        "It does not authorise procurement, inventory "
        "changes or financial approval."
    )