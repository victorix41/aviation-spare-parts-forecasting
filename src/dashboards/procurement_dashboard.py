"""Procurement Manager dashboard."""

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


def create_stockout_risk_chart(
    dataframe: pd.DataFrame,
):
    """Create procurement reviews by stockout risk."""

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

    summary["stockout_risk"] = pd.Categorical(
        summary["stockout_risk"],
        categories=RISK_ORDER,
        ordered=True,
    )

    summary = summary.sort_values(
        "stockout_risk"
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
        labels={
            "stockout_risk": "Stockout risk",
            "part_count": "Parts",
        },
        title="Procurement Reviews by Stockout Risk",
    )

    figure.update_traces(
        textposition="outside"
    )

    figure.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Number of parts",
    )

    return figure


def create_confidence_exposure_chart(
    dataframe: pd.DataFrame,
):
    """Create procurement exposure by forecast confidence."""

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
            ),
            part_count=(
                "part_number",
                "nunique",
            ),
        )
    )

    summary["forecast_confidence"] = pd.Categorical(
        summary["forecast_confidence"],
        categories=CONFIDENCE_ORDER,
        ordered=True,
    )

    summary = summary.sort_values(
        "forecast_confidence"
    )

    figure = px.bar(
        summary,
        x="forecast_confidence",
        y="procurement_value_usd",
        color="forecast_confidence",
        text="procurement_value_usd",
        custom_data=[
            "part_count",
        ],
        category_orders={
            "forecast_confidence": CONFIDENCE_ORDER,
        },
        color_discrete_map=CONFIDENCE_COLOURS,
        title="Procurement Exposure by Forecast Confidence",
    )

    figure.update_traces(
        texttemplate="USD %{text:,.0f}",
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Procurement exposure: USD %{y:,.2f}<br>"
            "Parts: %{customdata[0]}<extra></extra>"
        ),
    )

    figure.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title="USD",
    )

    return figure


def create_lead_time_chart(
    dataframe: pd.DataFrame,
):
    """Create the longest procurement lead-time chart."""

    prepared = (
        dataframe.sort_values(
            [
                "average_lead_time_days",
                "procurement_value_usd",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .head(15)
        .copy()
    )

    figure = px.bar(
        prepared,
        x="part_number",
        y="average_lead_time_days",
        color="stockout_risk",
        color_discrete_map=RISK_COLOURS,
        category_orders={
            "stockout_risk": RISK_ORDER,
        },
        title="Longest Procurement Lead-Time Reviews",
        hover_data={
            "description": True,
            "procurement_value_usd": ":,.2f",
            "forecast_confidence": True,
        },
    )

    figure.update_layout(
        xaxis_title=None,
        yaxis_title="Days",
        legend_title="Stockout risk",
    )

    return figure


def apply_filters(
    dataframe: pd.DataFrame,
    *,
    selected_risk: str,
    selected_confidence: str,
    minimum_value: float,
) -> pd.DataFrame:
    """Apply Procurement Manager dashboard filters."""

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

    filtered = filtered.loc[
        filtered["procurement_value_usd"]
        >= float(minimum_value)
    ]

    return (
        filtered.sort_values(
            [
                "procurement_priority",
                "procurement_value_usd",
                "part_number",
            ],
            ascending=[
                True,
                False,
                True,
            ],
        )
        .reset_index(drop=True)
    )


def render_procurement_dashboard(
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render the Procurement Manager dashboard."""

    st.title(
        "Procurement Manager Dashboard"
    )

    st.caption(
        "Prioritised order reviews, supplier lead-time exposure "
        "and assured procurement recommendations."
    )

    kpis = repository.load_procurement_kpis()

    first_row = st.columns(4)

    first_row[0].metric(
        "Order reviews",
        f"{kpis['recommendation_count']:,}",
    )
    first_row[1].metric(
        "Recommended units",
        format_quantity(
            kpis["recommended_order_quantity"]
        ),
    )
    first_row[2].metric(
        "Projected purchase value",
        format_currency(
            kpis["procurement_value_usd"]
        ),
    )
    first_row[3].metric(
        "Priority-one parts",
        f"{kpis['critical_priority_count']:,}",
    )

    second_row = st.columns(2)

    second_row[0].metric(
        "Long lead-time parts",
        f"{kpis['long_lead_time_count']:,}",
    )
    second_row[1].metric(
        "High-value reviews",
        f"{kpis['high_value_count']:,}",
    )

    st.divider()

    data = (
        repository
        .load_procurement_dashboard_data()
    )

    filter_columns = st.columns(3)

    selected_risk = filter_columns[0].selectbox(
        "Stockout risk",
        options=[
            "All",
            *RISK_ORDER,
        ],
        key="procurement_stockout_risk",
    )

    selected_confidence = (
        filter_columns[1].selectbox(
            "Forecast confidence",
            options=[
                "All",
                *CONFIDENCE_ORDER,
            ],
            key="procurement_forecast_confidence",
        )
    )

    minimum_value = (
        filter_columns[2].number_input(
            "Minimum procurement value",
            min_value=0.0,
            value=0.0,
            step=1000.0,
            key="procurement_minimum_value",
        )
    )

    filtered = apply_filters(
        data,
        selected_risk=selected_risk,
        selected_confidence=(
            selected_confidence
        ),
        minimum_value=minimum_value,
    )

    if filtered.empty:
        st.warning(
            "No procurement recommendations match "
            "the selected filters."
        )
    else:
        filtered_value = float(
            filtered[
                "procurement_value_usd"
            ].sum()
        )

        filtered_quantity = float(
            filtered[
                "recommended_order_quantity"
            ].sum()
        )

        filtered_summary = st.columns(3)

        filtered_summary[0].metric(
            "Filtered reviews",
            f"{len(filtered):,}",
        )
        filtered_summary[1].metric(
            "Filtered units",
            format_quantity(
                filtered_quantity
            ),
        )
        filtered_summary[2].metric(
            "Filtered purchase value",
            format_currency(
                filtered_value
            ),
        )

        chart_columns = st.columns(2)

        with chart_columns[0]:
            st.plotly_chart(
                create_stockout_risk_chart(
                    filtered
                ),
                width="stretch",
            )

        with chart_columns[1]:
            st.plotly_chart(
                create_confidence_exposure_chart(
                    filtered
                ),
                width="stretch",
            )

        st.plotly_chart(
            create_lead_time_chart(
                filtered
            ),
            width="stretch",
        )

    st.divider()

    st.subheader(
        "Procurement Review Queue"
    )

    if filtered.empty:
        st.info(
            "The procurement queue is empty for "
            "the selected filters."
        )
    else:
        display_dataframe(
            filtered,
            currency_columns=[
                "unit_price_usd",
                "procurement_value_usd",
            ],
            quantity_columns=[
                "current_balance",
                "recommended_order_quantity",
            ],
            height=550,
        )

    st.divider()

    st.subheader(
        "Procurement Agent Advisory"
    )

    advisories = (
        repository.load_role_recommendations(
            "Procurement Manager",
            limit=int(
                settings["display"][
                    "maximum_table_rows"
                ]
            ),
        )
    )

    if advisories.empty:
        st.success(
            "No assured Procurement Agent advisories "
            "are currently available."
        )
    else:
        display_dataframe(
            advisories,
            height=450,
        )

    st.divider()

    render_management_drilldown(
        repository=repository,
        title="Procurement Spare-Part Drill-Down",
    )

    render_management_alerts(
        repository=repository,
        settings=settings,
        target_role="Procurement Manager",
    )