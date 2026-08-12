"""Operations Manager dashboard."""

from __future__ import annotations

from pathlib import Path

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


def create_stock_cover_chart(
    dataframe: pd.DataFrame,
):
    """Create the lowest stock-cover chart."""

    prepared = (
        dataframe.sort_values(
            "months_of_stock_cover",
            ascending=True,
            na_position="first",
        )
        .head(20)
        .copy()
    )

    figure = px.bar(
        prepared,
        x="part_number",
        y="months_of_stock_cover",
        color="stockout_risk",
        color_discrete_map=RISK_COLOURS,
        category_orders={
            "stockout_risk": RISK_ORDER,
        },
        title="Lowest Stock-Cover Parts",
        hover_data={
            "description": True,
            "current_balance": True,
            "recommended_order_quantity": True,
        },
    )

    figure.update_layout(
        xaxis_title=None,
        yaxis_title="Months of stock cover",
    )

    return figure


def create_risk_timing_chart(
    dataframe: pd.DataFrame,
):
    """Create stockout timing distribution by risk."""

    relevant = dataframe.loc[
        dataframe["stockout_risk"].isin(
            [
                "Critical",
                "High",
                "Medium",
            ]
        )
    ].copy()

    figure = px.scatter(
        relevant,
        x="estimated_stockout_months",
        y="part_number",
        color="stockout_risk",
        size="recommended_order_quantity",
        color_discrete_map=RISK_COLOURS,
        category_orders={
            "stockout_risk": RISK_ORDER,
        },
        title="Estimated Stockout Timing",
        hover_data={
            "description": True,
            "current_balance": True,
            "average_lead_time_days": True,
        },
    )

    figure.update_layout(
        xaxis_title="Estimated stockout months",
        yaxis_title=None,
    )

    return figure


def create_lead_time_risk_chart(
    dataframe: pd.DataFrame,
):
    """Create operational lead-time exposure chart."""

    prepared = (
        dataframe.sort_values(
            "average_lead_time_days",
            ascending=False,
        )
        .head(20)
    )

    figure = px.bar(
        prepared,
        x="part_number",
        y="average_lead_time_days",
        color="stockout_risk",
        color_discrete_map=RISK_COLOURS,
        title="Operational Lead-Time Exposure",
    )

    figure.update_layout(
        xaxis_title=None,
        yaxis_title="Days",
    )

    return figure


def render_operations_dashboard(
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render the Operations Manager dashboard."""

    st.title(
        "Operations Manager Dashboard"
    )

    st.caption(
        "Maintenance readiness, stockout timing and "
        "operational contingency exposure."
    )

    kpis = repository.load_operations_kpis()

    columns = st.columns(5)

    columns[0].metric(
        "Critical stockouts",
        f"{kpis['critical_stockouts']:,}",
    )
    columns[1].metric(
        "High stock risks",
        f"{kpis['high_stockouts']:,}",
    )
    columns[2].metric(
        "Immediate exposure",
        f"{kpis['immediate_exposure']:,}",
    )
    columns[3].metric(
        "Near-term exposure",
        f"{kpis['near_term_exposure']:,}",
    )
    columns[4].metric(
        "Average months cover",
        f"{kpis['average_months_cover']:.2f}",
    )

    st.divider()

    data = (
        repository
        .load_operations_readiness_data()
    )

    if data.empty:
        st.info(
            "No operational stock-readiness records "
            "are currently available."
        )
    else:
        st.plotly_chart(
            create_stock_cover_chart(
                data
            ),
            width="stretch",
        )

        chart_columns = st.columns(2)

        with chart_columns[0]:
            st.plotly_chart(
                create_risk_timing_chart(
                    data
                ),
                width="stretch",
            )

        with chart_columns[1]:
            st.plotly_chart(
                create_lead_time_risk_chart(
                    data
                ),
                width="stretch",
            )

    st.subheader(
        "Maintenance Readiness Review"
    )

    display_dataframe(
        data,
        quantity_columns=[
            "current_balance",
            "recommended_order_quantity",
        ],
        height=540,
    )

    st.divider()

    st.subheader(
        "Operations Agent Advisory"
    )

    advisories = (
        repository.load_role_recommendations(
            "Operations Manager",
            limit=int(
                settings["display"][
                    "maximum_table_rows"
                ]
            ),
        )
    )

    if advisories.empty:
        st.success(
            "No assured Operations Agent advisories "
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
        audit_database_path=audit_database_path,
        decision_audit_settings=settings[
            "decision_audit"
        ],
        title="Operations Spare-Part Drill-Down",
        default_stockout_risk="Critical",
    )

    render_management_alerts(
        repository=repository,
        settings=settings,
        target_role="Operations Manager",
    )