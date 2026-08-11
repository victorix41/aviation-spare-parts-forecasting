"""Finance Manager dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboards.dashboard_utils import (
    display_dataframe,
    format_currency,
    format_quantity,
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


def create_risk_exposure_chart(
    dataframe: pd.DataFrame,
):
    """Create financial exposure by stockout risk."""

    summary = (
        dataframe.groupby(
            "stockout_risk",
            as_index=False,
            observed=False,
        )
        .agg(
            procurement_value_usd=(
                "procurement_value_usd",
                "sum",
            )
        )
    )

    figure = px.pie(
        summary,
        names="stockout_risk",
        values="procurement_value_usd",
        hole=0.52,
        color="stockout_risk",
        category_orders={
            "stockout_risk": RISK_ORDER,
        },
        color_discrete_map=RISK_COLOURS,
        title="Procurement Exposure by Risk",
    )

    figure.update_traces(
        textinfo="label+percent",
    )

    return figure


def create_confidence_exposure_chart(
    dataframe: pd.DataFrame,
):
    """Create financial exposure by forecast confidence."""

    summary = (
        dataframe.groupby(
            "forecast_confidence",
            as_index=False,
            observed=False,
        )
        .agg(
            procurement_value_usd=(
                "procurement_value_usd",
                "sum",
            )
        )
    )

    figure = px.bar(
        summary,
        x="forecast_confidence",
        y="procurement_value_usd",
        color="forecast_confidence",
        text="procurement_value_usd",
        category_orders={
            "forecast_confidence": CONFIDENCE_ORDER,
        },
        color_discrete_map=CONFIDENCE_COLOURS,
        title="Procurement Exposure by Forecast Confidence",
    )

    figure.update_traces(
        texttemplate="USD %{text:,.0f}",
        textposition="outside",
    )

    figure.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title="USD",
    )

    return figure


def create_top_exposure_chart(
    dataframe: pd.DataFrame,
):
    """Create the highest-value procurement exposure chart."""

    prepared = (
        dataframe.sort_values(
            "procurement_value_usd",
            ascending=False,
        )
        .head(15)
        .sort_values(
            "procurement_value_usd",
            ascending=True,
        )
    )

    figure = px.bar(
        prepared,
        x="procurement_value_usd",
        y="part_number",
        orientation="h",
        color="stockout_risk",
        color_discrete_map=RISK_COLOURS,
        title="Highest Part-Level Procurement Exposure",
        hover_data={
            "description": True,
            "forecast_confidence": True,
        },
    )

    figure.update_layout(
        xaxis_title="USD",
        yaxis_title=None,
    )

    return figure


def render_finance_dashboard(
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render the Finance Manager dashboard."""

    st.title(
        "Finance Manager Dashboard"
    )

    st.caption(
        "Inventory valuation, procurement exposure, budget risk "
        "and forecast-confidence review."
    )

    kpis = repository.load_finance_kpis()

    columns = st.columns(5)

    columns[0].metric(
        "Inventory value",
        format_currency(
            kpis["inventory_value_usd"]
        ),
    )
    columns[1].metric(
        "Procurement exposure",
        format_currency(
            kpis["procurement_value_usd"]
        ),
    )
    columns[2].metric(
        "Recommended units",
        format_quantity(
            kpis["recommended_order_quantity"]
        ),
    )
    columns[3].metric(
        "Six-figure reviews",
        f"{kpis['six_figure_orders']:,}",
    )
    columns[4].metric(
        "Low-confidence exposure",
        format_currency(
            kpis["low_confidence_exposure_usd"]
        ),
    )

    st.divider()

    exposure = (
        repository.load_finance_exposure()
    )

    if exposure.empty:
        st.info(
            "No current financial procurement exposure "
            "is available."
        )
    else:
        chart_columns = st.columns(2)

        with chart_columns[0]:
            st.plotly_chart(
                create_risk_exposure_chart(
                    exposure
                ),
                width="stretch",
            )

        with chart_columns[1]:
            st.plotly_chart(
                create_confidence_exposure_chart(
                    exposure
                ),
                width="stretch",
            )

        st.plotly_chart(
            create_top_exposure_chart(
                exposure
            ),
            width="stretch",
        )

    st.subheader(
        "Financial Exposure by Spare Part"
    )

    display_dataframe(
        exposure,
        currency_columns=[
            "inventory_value_usd",
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
        "Finance Agent Advisory"
    )

    advisories = (
        repository.load_role_recommendations(
            "Finance Manager",
            limit=int(
                settings["display"][
                    "maximum_table_rows"
                ]
            ),
        )
    )

    if advisories.empty:
        st.success(
            "No assured Finance Agent advisories "
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
        title="Finance Spare-Part Drill-Down",
    )

    render_management_alerts(
        repository=repository,
        settings=settings,
        target_role="Finance Manager",
    )