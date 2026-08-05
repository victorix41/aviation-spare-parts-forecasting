"""Shared formatting and visualisation utilities for Streamlit dashboards."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


def format_currency(
    value: float | int | None,
    currency: str = "USD",
) -> str:
    """Format a currency value consistently."""

    numeric_value = float(value or 0.0)

    return f"{currency} {numeric_value:,.2f}"


def format_quantity(
    value: float | int | None,
) -> str:
    """Format a quantity without unnecessary decimals."""

    numeric_value = float(value or 0.0)

    return f"{numeric_value:,.0f}"


def render_governance_notice() -> None:
    """Display mandatory management-governance information."""

    st.warning(
        "Decision-support system only. Forecasts, optimisation outputs "
        "and agent recommendations require authorised human review. "
        "The application cannot create purchase orders, modify inventory "
        "records or approve expenditure."
    )


def render_status_badge(
    label: str,
    value: str,
) -> None:
    """Render a compact status message."""

    st.markdown(
        f"**{label}:** `{value}`"
    )


def prepare_risk_summary(
    dataframe: pd.DataFrame,
    risk_order: list[str],
) -> pd.DataFrame:
    """Apply the configured risk order."""

    output = dataframe.copy()

    output["stockout_risk"] = pd.Categorical(
        output["stockout_risk"],
        categories=risk_order,
        ordered=True,
    )

    return output.sort_values(
        "stockout_risk"
    ).reset_index(drop=True)


def create_risk_chart(
    dataframe: pd.DataFrame,
    risk_order: list[str],
    risk_colours: dict[str, str],
):
    """Create the management stock-risk chart."""

    prepared = prepare_risk_summary(
        dataframe,
        risk_order,
    )

    figure = px.bar(
        prepared,
        x="stockout_risk",
        y="part_count",
        color="stockout_risk",
        text="part_count",
        category_orders={
            "stockout_risk": risk_order,
        },
        color_discrete_map=risk_colours,
        labels={
            "stockout_risk": "Stockout risk",
            "part_count": "Parts",
        },
    )

    figure.update_traces(
        textposition="outside"
    )

    figure.update_layout(
        title="Forecast-Active Parts by Stockout Risk",
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Number of parts",
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 20,
        },
    )

    return figure


def create_procurement_exposure_chart(
    dataframe: pd.DataFrame,
    risk_order: list[str],
    risk_colours: dict[str, str],
):
    """Create procurement exposure by risk category."""

    prepared = prepare_risk_summary(
        dataframe,
        risk_order,
    )

    figure = px.bar(
        prepared,
        x="stockout_risk",
        y="procurement_value_usd",
        color="stockout_risk",
        category_orders={
            "stockout_risk": risk_order,
        },
        color_discrete_map=risk_colours,
        labels={
            "stockout_risk": "Stockout risk",
            "procurement_value_usd": (
                "Projected procurement value (USD)"
            ),
        },
    )

    figure.update_layout(
        title="Projected Procurement Exposure by Risk",
        showlegend=False,
        xaxis_title=None,
        yaxis_title="USD",
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 20,
        },
    )

    return figure


def create_model_distribution_chart(
    dataframe: pd.DataFrame,
):
    """Create selected-model distribution chart."""

    figure = px.bar(
        dataframe,
        x="selected_model",
        y="part_count",
        color="selected_model",
        text="part_count",
        labels={
            "selected_model": "Selected model",
            "part_count": "Parts",
        },
    )

    figure.update_traces(
        textposition="outside"
    )

    figure.update_layout(
        title="Selected Forecast Models",
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Number of parts",
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 20,
        },
    )

    return figure


def display_dataframe(
    dataframe: pd.DataFrame,
    *,
    currency_columns: list[str] | None = None,
    quantity_columns: list[str] | None = None,
    height: int = 400,
) -> None:
    """Display a formatted Streamlit dataframe."""

    currency_columns = currency_columns or []
    quantity_columns = quantity_columns or []

    column_configuration: dict[str, Any] = {}

    for column in currency_columns:
        if column in dataframe.columns:
            column_configuration[column] = (
                st.column_config.NumberColumn(
                    column.replace("_", " ").title(),
                    format="$%.2f",
                )
            )

    for column in quantity_columns:
        if column in dataframe.columns:
            column_configuration[column] = (
                st.column_config.NumberColumn(
                    column.replace("_", " ").title(),
                    format="%.0f",
                )
            )

    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True,
        column_config=column_configuration,
        height=height,
    )

def create_forecast_confidence_chart(
    dataframe: pd.DataFrame,
):
    """Create forecast-confidence distribution chart."""

    confidence_order = [
        "High",
        "Medium",
        "Low",
    ]

    confidence_colours = {
        "High": "#70AD47",
        "Medium": "#FFC000",
        "Low": "#ED7D31",
    }

    prepared = dataframe.copy()

    prepared["forecast_confidence"] = pd.Categorical(
        prepared["forecast_confidence"],
        categories=confidence_order,
        ordered=True,
    )

    prepared = prepared.sort_values(
        "forecast_confidence"
    )

    figure = px.pie(
        prepared,
        names="forecast_confidence",
        values="part_count",
        hole=0.55,
        category_orders={
            "forecast_confidence": confidence_order,
        },
        color="forecast_confidence",
        color_discrete_map=confidence_colours,
    )

    figure.update_traces(
        textposition="inside",
        textinfo="label+value+percent",
    )

    figure.update_layout(
        title="Forecast Confidence",
        showlegend=False,
        margin={
            "l": 10,
            "r": 10,
            "t": 60,
            "b": 10,
        },
    )

    return figure

def create_advisory_priority_chart(
    dataframe: pd.DataFrame,
    risk_colours: dict[str, str],
):
    """Create assured advisory distribution by priority."""

    priority_order = [
        "Critical",
        "High",
        "Medium",
        "Low",
    ]

    prepared = dataframe.copy()

    prepared["priority"] = pd.Categorical(
        prepared["priority"],
        categories=priority_order,
        ordered=True,
    )

    prepared = prepared.sort_values(
        "priority"
    )

    figure = px.bar(
        prepared,
        x="priority",
        y="recommendation_count",
        color="priority",
        text="recommendation_count",
        category_orders={
            "priority": priority_order,
        },
        color_discrete_map=risk_colours,
        labels={
            "priority": "Priority",
            "recommendation_count": "Advisories",
        },
    )

    figure.update_traces(
        textposition="outside"
    )

    figure.update_layout(
        title="Assured Advisories by Priority",
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Number of advisories",
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 20,
        },
    )

    return figure

def determine_readiness_status(
    *,
    critical_parts: int,
    high_risk_parts: int,
    procurement_exposure_usd: float,
    settings: dict,
) -> tuple[str, str, str]:
    """Determine an executive spare-parts readiness status."""

    red = (
        critical_parts
        >= int(
            settings[
                "critical_parts_red_threshold"
            ]
        )
        or high_risk_parts
        >= int(
            settings[
                "high_risk_parts_red_threshold"
            ]
        )
        or procurement_exposure_usd
        >= float(
            settings[
                "procurement_exposure_red_usd"
            ]
        )
    )

    amber = (
        critical_parts
        >= int(
            settings[
                "critical_parts_amber_threshold"
            ]
        )
        or high_risk_parts
        >= int(
            settings[
                "high_risk_parts_amber_threshold"
            ]
        )
        or procurement_exposure_usd
        >= float(
            settings[
                "procurement_exposure_amber_usd"
            ]
        )
    )

    if red:
        return (
            "Critical Attention",
            "🔴",
            (
                "Immediate cross-functional management "
                "review is required."
            ),
        )

    if amber:
        return (
            "Management Attention",
            "🟠",
            (
                "Elevated stock and procurement exposure "
                "requires coordinated monitoring."
            ),
        )

    return (
        "Stable",
        "🟢",
        (
            "No material portfolio-level spare-parts "
            "exception is currently identified."
        ),
    )

def apply_dashboard_styling() -> None:
    """Apply executive-dashboard presentation styling."""

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
        }

        div[data-testid="stMetric"] {
            background-color: #F7F9FC;
            border: 1px solid #E1E6ED;
            border-radius: 8px;
            padding: 12px 14px;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.65rem;
            font-weight: 650;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 0.88rem;
            font-weight: 600;
        }

        h1 {
            margin-bottom: 0.2rem;
        }

        h2, h3 {
            margin-top: 0.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )