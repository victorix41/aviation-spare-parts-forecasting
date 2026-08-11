"""Quality Manager dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboards.dashboard_utils import (
    display_dataframe,
)
from src.dashboards.data_access import DashboardRepository

from src.dashboards.management_drilldown import (
    render_management_drilldown,
)

from src.dashboards.management_alerts import (
    render_management_alerts,
)


RISK_ORDER = [
    "Critical",
    "High",
    "Medium",
    "Low",
]

RISK_COLOURS = {
    "Critical": "#C00000",
    "High": "#ED7D31",
    "Medium": "#FFC000",
    "Low": "#70AD47",
}

CONFIDENCE_ORDER = [
    "High",
    "Medium",
    "Low",
]

CONFIDENCE_COLOURS = {
    "High": "#70AD47",
    "Medium": "#5B9BD5",
    "Low": "#ED7D31",
}

CRITICALITY_ORDER = [
    "Critical",
    "High",
    "Medium",
    "Low",
    "Unspecified",
]

CRITICALITY_COLOURS = {
    "Critical": "#C00000",
    "High": "#ED7D31",
    "Medium": "#FFC000",
    "Low": "#70AD47",
    "Unspecified": "#A5A5A5",
}


def create_quality_risk_chart(
    dataframe: pd.DataFrame,
):
    """Create quality-review count by stockout risk."""

    summary = (
        dataframe.groupby(
            "stockout_risk",
            as_index=False,
            observed=False,
        )
        .agg(
            part_count=(
                "part_number",
                "nunique",
            )
        )
    )

    figure = px.bar(
        summary,
        x="stockout_risk",
        y="part_count",
        color="stockout_risk",
        text="part_count",
        category_orders={
            "stockout_risk": RISK_ORDER,
        },
        color_discrete_map=RISK_COLOURS,
        title="Quality Reviews by Stockout Risk",
    )

    figure.update_traces(
        textposition="outside"
    )

    figure.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Parts",
    )

    return figure


def create_quality_confidence_chart(
    dataframe: pd.DataFrame,
):
    """Create quality reviews by forecast confidence."""

    summary = (
        dataframe.groupby(
            "forecast_confidence",
            as_index=False,
            observed=False,
        )
        .agg(
            part_count=(
                "part_number",
                "nunique",
            )
        )
    )

    figure = px.bar(
        summary,
        x="forecast_confidence",
        y="part_count",
        color="forecast_confidence",
        text="part_count",
        category_orders={
            "forecast_confidence": CONFIDENCE_ORDER,
        },
        color_discrete_map=CONFIDENCE_COLOURS,
        title="Quality Reviews by Forecast Confidence",
    )

    figure.update_traces(
        textposition="outside"
    )

    figure.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Parts",
    )

    return figure


def create_assurance_outcome_chart(
    *,
    assurance_passed: int,
    assurance_failed: int,
):
    """Create the agent-assurance outcome chart."""

    dataframe = pd.DataFrame(
        {
            "assurance_status": [
                "Passed",
                "Failed",
            ],
            "finding_count": [
                int(assurance_passed),
                int(assurance_failed),
            ],
        }
    )

    figure = px.pie(
        dataframe,
        names="assurance_status",
        values="finding_count",
        hole=0.55,
        color="assurance_status",
        color_discrete_map={
            "Passed": "#70AD47",
            "Failed": "#C00000",
        },
        title="Agent Assurance Outcomes",
    )

    figure.update_traces(
        textinfo="label+value+percent",
    )

    return figure


def create_criticality_chart(
    dataframe: pd.DataFrame,
):
    """Create quality reviews by engineering criticality."""

    summary = (
        dataframe.groupby(
            "engineering_criticality",
            as_index=False,
            observed=False,
        )
        .agg(
            part_count=(
                "part_number",
                "nunique",
            )
        )
    )

    figure = px.bar(
        summary,
        x="engineering_criticality",
        y="part_count",
        color="engineering_criticality",
        text="part_count",
        category_orders={
            "engineering_criticality": (
                CRITICALITY_ORDER
            ),
        },
        color_discrete_map=(
            CRITICALITY_COLOURS
        ),
        title="Quality Reviews by Engineering Criticality",
    )

    figure.update_traces(
        textposition="outside"
    )

    figure.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Parts",
    )

    return figure


def apply_quality_filters(
    dataframe: pd.DataFrame,
    *,
    selected_risk: str,
    selected_confidence: str,
    selected_criticality: str,
) -> pd.DataFrame:
    """Apply Quality Manager dashboard filters."""

    filtered = dataframe.copy()

    if selected_risk != "All":
        filtered = filtered.loc[
            filtered["stockout_risk"]
            == selected_risk
        ]

    if selected_confidence != "All":
        filtered = filtered.loc[
            filtered["forecast_confidence"]
            == selected_confidence
        ]

    if selected_criticality != "All":
        filtered = filtered.loc[
            filtered["engineering_criticality"]
            == selected_criticality
        ]

    return (
        filtered.sort_values(
            [
                "stockout_risk",
                "engineering_criticality",
                "procurement_value_usd",
                "part_number",
            ],
            ascending=[
                True,
                True,
                False,
                True,
            ],
        )
        .reset_index(drop=True)
    )


def render_quality_dashboard(
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render the Quality Manager dashboard."""

    st.title(
        "Quality Manager Dashboard"
    )

    st.caption(
        "Governance, traceability, assurance and "
        "human-approval oversight."
    )

    kpis = repository.load_quality_kpis()

    columns = st.columns(6)

    columns[0].metric(
        "Order reviews",
        f"{kpis['order_review_records']:,}",
    )
    columns[1].metric(
        "Human approvals",
        f"{kpis['human_approval_records']:,}",
    )
    columns[2].metric(
        "Low-confidence orders",
        f"{kpis['low_confidence_orders']:,}",
    )
    columns[3].metric(
        "Automatic actions",
        f"{kpis['automatic_actions_allowed']:,}",
    )
    columns[4].metric(
        "Assurance passed",
        f"{kpis['assurance_passed']:,}",
    )
    columns[5].metric(
        "Assurance failed",
        f"{kpis['assurance_failed']:,}",
    )

    if (
        kpis["automatic_actions_allowed"]
        == 0
    ):
        st.success(
            "Governance control confirmed: no automatic "
            "purchase-order action is enabled."
        )
    else:
        st.error(
            "Governance exception detected: one or more "
            "automatic actions are enabled."
        )

    st.divider()

    data = (
        repository
        .load_quality_review_data()
    )

    filter_columns = st.columns(3)

    selected_risk = (
        filter_columns[0].selectbox(
            "Stockout risk",
            options=[
                "All",
                *RISK_ORDER,
            ],
            key="quality_stockout_risk",
        )
    )

    selected_confidence = (
        filter_columns[1].selectbox(
            "Forecast confidence",
            options=[
                "All",
                *CONFIDENCE_ORDER,
            ],
            key="quality_forecast_confidence",
        )
    )

    selected_criticality = (
        filter_columns[2].selectbox(
            "Engineering criticality",
            options=[
                "All",
                *CRITICALITY_ORDER,
            ],
            key="quality_engineering_criticality",
        )
    )

    filtered = apply_quality_filters(
        data,
        selected_risk=selected_risk,
        selected_confidence=(
            selected_confidence
        ),
        selected_criticality=(
            selected_criticality
        ),
    )

    low_confidence_count = int(
        (
            filtered["forecast_confidence"]
            == "Low"
        ).sum()
    )

    critical_risk_count = int(
        (
            filtered["stockout_risk"]
            == "Critical"
        ).sum()
    )

    filtered_summary = st.columns(3)

    filtered_summary[0].metric(
        "Filtered quality reviews",
        f"{len(filtered):,}",
    )
    filtered_summary[1].metric(
        "Filtered low-confidence parts",
        f"{low_confidence_count:,}",
    )
    filtered_summary[2].metric(
        "Filtered critical-risk parts",
        f"{critical_risk_count:,}",
    )

    st.divider()

    if filtered.empty:
        st.warning(
            "No quality-review records match "
            "the selected filters."
        )
    else:
        first_chart_row = st.columns(2)

        with first_chart_row[0]:
            st.plotly_chart(
                create_quality_risk_chart(
                    filtered
                ),
                width="stretch",
            )

        with first_chart_row[1]:
            st.plotly_chart(
                create_quality_confidence_chart(
                    filtered
                ),
                width="stretch",
            )

        second_chart_row = st.columns(2)

        with second_chart_row[0]:
            st.plotly_chart(
                create_assurance_outcome_chart(
                    assurance_passed=int(
                        kpis["assurance_passed"]
                    ),
                    assurance_failed=int(
                        kpis["assurance_failed"]
                    ),
                ),
                width="stretch",
            )

        with second_chart_row[1]:
            st.plotly_chart(
                create_criticality_chart(
                    filtered
                ),
                width="stretch",
            )

    st.divider()

    st.subheader(
        "Quality and Traceability Review Queue"
    )

    if filtered.empty:
        st.info(
            "The quality-review queue is empty "
            "for the selected filters."
        )
    else:
        display_dataframe(
            filtered,
            currency_columns=[
                "procurement_value_usd",
            ],
            quantity_columns=[
                "recommended_order_quantity",
            ],
            height=520,
        )

    st.divider()

    st.subheader(
        "Quality Agent Advisory"
    )

    advisories = (
        repository.load_role_recommendations(
            "Quality Manager",
            limit=int(
                settings["display"][
                    "maximum_table_rows"
                ]
            ),
        )
    )

    if advisories.empty:
        st.success(
            "No assured Quality Agent advisories "
            "are currently available."
        )
    else:
        display_dataframe(
            advisories,
            height=420,
        )

    with st.expander(
        "Quality governance interpretation"
    ):
        st.markdown(
            """
            The dashboard confirms only that recommendations
            passed the configured system assurance checks.

            It does not replace:

            - approved-supplier verification;
            - certification and traceability review;
            - receiving inspection;
            - shelf-life control;
            - airworthiness-document review;
            - authorised release requirements; or
            - independent management approval.
            """
        )

    st.divider()

    render_management_drilldown(
        repository=repository,
        title="Quality Spare-Part Drill-Down",
    )

    render_management_alerts(
        repository=repository,
        settings=settings,
        target_role="Quality Manager",
    )