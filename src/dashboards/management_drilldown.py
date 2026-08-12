"""Reusable management spare-part drill-down."""

from __future__ import annotations

from pathlib import Path

import math

import pandas as pd
import streamlit as st

from src.dashboards.dashboard_utils import (
    create_part_demand_history_chart,
    create_part_inventory_position_chart,
    display_dataframe,
    format_currency,
    format_quantity,
)
from src.dashboards.data_access import (
    DashboardRepository,

)

from src.dashboards.forecast_explainability import (
    render_forecast_explainability,
)

from src.dashboards.advisory_traceability import (
    render_advisory_traceability,
)

from src.dashboards.decision_audit_dashboard import (
    render_decision_audit,
)

def _is_missing(
    value: object,
) -> bool:
    """Return True when a value is null or NaN."""

    if value is None:
        return True

    try:
        return bool(
            pd.isna(value)
        )
    except (
        TypeError,
        ValueError,
    ):
        return False


def _format_decimal(
    value: object,
    *,
    decimals: int = 2,
) -> str:
    """Safely format a decimal value."""

    if _is_missing(value):
        return "N/A"

    try:
        numeric_value = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return str(value)

    if not math.isfinite(
        numeric_value
    ):
        return "N/A"

    return (
        f"{numeric_value:,.{decimals}f}"
    )


def _format_days(
    value: object,
) -> str:
    """Safely format a number of days."""

    if _is_missing(value):
        return "N/A"

    try:
        numeric_value = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return str(value)

    if not math.isfinite(
        numeric_value
    ):
        return "N/A"

    return f"{numeric_value:,.0f} days"


def _safe_text(
    value: object,
    *,
    default: str = "Unavailable",
) -> str:
    """Safely convert a value to readable text."""

    if _is_missing(value):
        return default

    text = str(value).strip()

    return (
        text
        if text
        else default
    )


def render_management_drilldown(
    *,
    repository: DashboardRepository,
    audit_database_path: Path,
    decision_audit_settings: dict,
    title: str = "Management Drill-Down",
    default_stockout_risk: str | None = None,
) -> None:
    """Render portfolio-to-part management drill-down."""

    st.subheader(
        title
    )

    filter_columns = st.columns(3)

    risk_options = [
        "All",
        "Critical",
        "High",
        "Medium",
        "Low",
    ]

    default_risk_index = 0

    if (
        default_stockout_risk
        in risk_options
    ):
        default_risk_index = (
            risk_options.index(
                default_stockout_risk
            )
        )

    selected_risk = (
        filter_columns[0].selectbox(
            "Stockout risk",
            options=risk_options,
            index=default_risk_index,
            key=f"{title}_risk",
        )
    )

    selected_criticality = (
        filter_columns[1].selectbox(
            "Engineering criticality",
            options=[
                "All",
                "Critical",
                "High",
                "Medium",
                "Low",
                "Unspecified",
            ],
            key=f"{title}_criticality",
        )
    )

    selected_confidence = (
        filter_columns[2].selectbox(
            "Forecast confidence",
            options=[
                "All",
                "High",
                "Medium",
                "Low",
            ],
            key=f"{title}_confidence",
        )
    )

    parts = (
        repository
        .load_management_drilldown_parts(
            stockout_risk=(
                None
                if selected_risk == "All"
                else selected_risk
            ),
            engineering_criticality=(
                None
                if selected_criticality
                == "All"
                else selected_criticality
            ),
            forecast_confidence=(
                None
                if selected_confidence
                == "All"
                else selected_confidence
            ),
            limit=100,
        )
    )

    if parts.empty:
        st.info(
            "No spare parts match "
            "the selected filters."
        )
        return

    st.markdown(
        "**Filtered Spare-Parts Portfolio**"
    )

    display_dataframe(
        parts,
        currency_columns=[
            "procurement_value_usd",
        ],
        quantity_columns=[
            "current_balance",
            "recommended_order_quantity",
        ],
        height=360,
    )

    labels: dict[str, str] = {}

    for row in parts.itertuples(
        index=False
    ):
        part_number = _safe_text(
            getattr(
                row,
                "part_number",
                None,
            )
        )

        description = _safe_text(
            getattr(
                row,
                "description",
                None,
            ),
            default="No description",
        )

        stockout_risk = _safe_text(
            getattr(
                row,
                "stockout_risk",
                None,
            )
        )

        label = (
            f"{part_number} — "
            f"{description} "
            f"[{stockout_risk}]"
        )

        labels[label] = (
            part_number
        )

    selected_label = st.selectbox(
        "Select spare part for detailed review",
        options=list(
            labels.keys()
        ),
        key=f"{title}_part",
    )

    part_number = labels[
        selected_label
    ]

    details = (
        repository
        .load_part_decision_record(
            part_number
        )
    )

    if details.empty:
        st.warning(
            "No decision record was found "
            "for the selected spare part."
        )
        return

    row = details.iloc[0]

    part_number_display = (
        _safe_text(
            row.get(
                "part_number"
            )
        )
    )

    description_display = (
        _safe_text(
            row.get(
                "description"
            ),
            default="No description",
        )
    )

    st.markdown(
        f"### {part_number_display} — "
        f"{description_display}"
    )

    stockout_risk = _safe_text(
        row.get(
            "stockout_risk"
        )
    )

    current_balance = row.get(
        "current_balance"
    )

    months_cover = row.get(
        "months_of_stock_cover"
    )

    months_cover_display = (
        _format_decimal(
            months_cover,
            decimals=2,
        )
    )

    recommended_order = row.get(
        "recommended_order_quantity"
    )

    procurement_value = row.get(
        "procurement_value_usd"
    )

    first_row = st.columns(5)

    first_row[0].metric(
        "Stockout risk",
        stockout_risk,
    )

    first_row[1].metric(
        "Current balance",
        format_quantity(
            current_balance
        ),
    )

    first_row[2].metric(
        "Months cover",
        months_cover_display,
    )

    first_row[3].metric(
        "Recommended order",
        format_quantity(
            recommended_order
        ),
    )

    first_row[4].metric(
        "Procurement value",
        format_currency(
            procurement_value
        ),
    )

    engineering_criticality = (
        _safe_text(
            row.get(
                "engineering_criticality"
            )
        )
    )

    forecast_confidence = (
        _safe_text(
            row.get(
                "forecast_confidence"
            )
        )
    )

    selected_model = (
        _safe_text(
            row.get(
                "selected_forecast_model"
            )
        )
    )

    lead_time_days = row.get(
        "average_lead_time_days"
    )

    lead_time_display = (
        _format_days(
            lead_time_days
        )
    )

    second_row = st.columns(4)

    second_row[0].metric(
        "Engineering criticality",
        engineering_criticality,
    )

    second_row[1].metric(
        "Forecast confidence",
        forecast_confidence,
    )

    second_row[2].metric(
        "Selected model",
        selected_model,
    )

    second_row[3].metric(
        "Lead time",
        lead_time_display,
    )

    st.divider()

    render_forecast_explainability(
        repository=repository,
        part_number=part_number,
    )

    st.divider()

    history = (
        repository
        .load_part_forecast_history(
            part_number
        )
    )

    chart_columns = st.columns(2)

    with chart_columns[0]:
        if history.empty:
            st.info(
                "No historical demand "
                "is available."
            )
        else:
            history_figure = (
                create_part_demand_history_chart(
                    history
                )
            )

            st.plotly_chart(
                history_figure,
                width="stretch",
            )

    with chart_columns[1]:
        inventory_figure = (
            create_part_inventory_position_chart(
                row
            )
        )

        st.plotly_chart(
            inventory_figure,
            width="stretch",
        )

    st.divider()

    st.markdown(
        "**Decision-Support Details**"
    )

    detail_columns = st.columns(4)

    average_monthly_demand = (
        row.get(
            "average_monthly_demand"
        )
    )

    safety_stock = row.get(
        "safety_stock"
    )

    reorder_point = row.get(
        "reorder_point"
    )

    estimated_stockout_months = row.get(
        "estimated_stockout_months"
    )

    if _is_missing(
        estimated_stockout_months
    ):
        estimated_stockout_display = "N/A"
    else:
        estimated_stockout_value = (
            _format_decimal(
                estimated_stockout_months,
                decimals=2,
            )
        )

        estimated_stockout_display = (
            estimated_stockout_value
            + " months"
        )

    detail_columns[0].metric(
        "Average monthly demand",
        _format_decimal(
            average_monthly_demand,
            decimals=2,
        ),
    )

    detail_columns[1].metric(
        "Safety stock",
        _format_decimal(
            safety_stock,
            decimals=2,
        ),
    )

    detail_columns[2].metric(
        "Reorder point",
        _format_decimal(
            reorder_point,
            decimals=2,
        ),
    )

    detail_columns[3].metric(
        "Estimated stockout",
        estimated_stockout_display,
    )

    st.markdown(
            "**Recommendation rationale**"
    )

    recommendation_reason = (
        _safe_text(
            row.get(
                "recommendation_reason"
            ),
            default=(
                "No recommendation rationale "
                "is available."
            ),
        )
    )

    st.info(
        recommendation_reason
    )

    recommendation_status = (
        _safe_text(
            row.get(
                "recommendation_status"
            )
        )
    )

    st.caption(
        "Recommendation status: "
        f"{recommendation_status}"
    )

    advisories = (
        repository
        .load_part_agent_advisories(
            part_number
        )
    )

    st.markdown(
        "**Agent Advisory Evidence**"
    )

    if advisories.empty:
        st.info(
            "No assured part-level agent "
            "advisory is available."
        )

    else:
        display_dataframe(
            advisories,
            height=360,
        )

        st.caption(
            "Agent recommendations are "
            "decision-support outputs only. "
            "Human approval remains required."
        )

    st.divider()

    render_advisory_traceability(
        repository=repository,
        part_number=part_number,
    )

    st.divider()

    render_decision_audit(
        repository=repository,
        audit_database_path=audit_database_path,
        part_number=part_number,
        settings={
            "decision_audit": (
                decision_audit_settings
            ),
        },
    )