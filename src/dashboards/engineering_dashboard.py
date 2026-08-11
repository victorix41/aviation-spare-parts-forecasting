"""Engineering Manager dashboard."""

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


CRITICALITY_ORDER = [
    "Critical",
    "High",
    "Medium",
    "Low",
    "Unspecified",
]

CRITICALITY_COLOURS = {
    "Critical": "#C00000",
    "High": "#5B9BD5",
    "Medium": "#FFC000",
    "Low": "#70AD47",
    "Unspecified": "#A5A5A5",
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


def create_criticality_chart(
    dataframe: pd.DataFrame,
):
    """Create engineering-criticality distribution."""

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
        title="Parts by Engineering Criticality",
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


def create_model_chart(
    dataframe: pd.DataFrame,
):
    """Create forecast-model distribution for engineering parts."""

    summary = (
        dataframe.groupby(
            "selected_forecast_model",
            as_index=False,
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
        x="selected_forecast_model",
        y="part_count",
        text="part_count",
        title="Forecast Models for Critical Parts",
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


def create_confidence_chart(
    dataframe: pd.DataFrame,
):
    """Create confidence distribution for engineering reviews."""

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

    figure = px.pie(
        summary,
        names="forecast_confidence",
        values="part_count",
        hole=0.5,
        color="forecast_confidence",
        category_orders={
            "forecast_confidence": CONFIDENCE_ORDER,
        },
        color_discrete_map=CONFIDENCE_COLOURS,
        title="Engineering Review Forecast Confidence",
    )

    figure.update_traces(
        textinfo="label+value+percent",
    )

    return figure


def render_engineering_dashboard(
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render the Engineering Manager dashboard."""

    st.title(
        "Engineering Manager Dashboard"
    )

    st.caption(
        "Technical criticality, forecast assumptions and "
        "engineering requirement validation."
    )

    kpis = repository.load_engineering_kpis()

    columns = st.columns(4)

    columns[0].metric(
        "Critical parts",
        f"{kpis['critical_parts']:,}",
    )
    columns[1].metric(
        "High-criticality parts",
        f"{kpis['high_criticality_parts']:,}",
    )
    columns[2].metric(
        "Engineering reviews",
        f"{kpis['engineering_reviews']:,}",
    )
    columns[3].metric(
        "Low-confidence critical parts",
        f"{kpis['low_confidence_critical_parts']:,}",
    )

    st.divider()

    data = (
        repository
        .load_engineering_review_data()
    )

    if data.empty:
        st.info(
            "No Critical or High engineering review "
            "records are currently available."
        )
    else:
        first_chart_row = st.columns(2)

        with first_chart_row[0]:
            st.plotly_chart(
                create_criticality_chart(
                    data
                ),
                width="stretch",
            )

        with first_chart_row[1]:
            st.plotly_chart(
                create_model_chart(
                    data
                ),
                width="stretch",
            )

        st.plotly_chart(
            create_confidence_chart(
                data
            ),
            width="stretch",
        )

    st.subheader(
        "Technical Requirement Review"
    )

    display_dataframe(
        data,
        currency_columns=[
            "procurement_value_usd",
        ],
        quantity_columns=[
            "current_balance",
            "recommended_order_quantity",
        ],
        height=520,
    )

    st.divider()

    st.subheader(
        "Engineering Agent Advisory"
    )

    advisories = (
        repository.load_role_recommendations(
            "Engineering Manager",
            limit=int(
                settings["display"][
                    "maximum_table_rows"
                ]
            ),
        )
    )

    if advisories.empty:
        st.success(
            "No assured Engineering Agent advisories "
            "are currently available."
        )
    else:
        display_dataframe(
            advisories,
            height=420,
        )

    st.divider()

    render_management_drilldown(
        repository=repository,
        title="Engineering Spare-Part Drill-Down",
        default_stockout_risk="High",
    )

    render_management_alerts(
        repository=repository,
        settings=settings,
        target_role="Engineering Manager",
    )