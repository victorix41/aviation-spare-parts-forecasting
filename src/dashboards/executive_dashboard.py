"""Accountable Manager executive dashboard."""

from __future__ import annotations

import streamlit as st

from src.dashboards.dashboard_utils import (
    create_advisory_priority_chart,
    create_forecast_confidence_chart,
    create_model_distribution_chart,
    create_procurement_exposure_chart,
    create_risk_chart,
    determine_readiness_status,
    display_dataframe,
    format_currency,
    format_quantity,
)
from src.dashboards.data_access import DashboardRepository


def render_readiness_header(
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render portfolio readiness and data-refresh information."""

    kpis = repository.load_executive_kpis()

    status, icon, explanation = determine_readiness_status(
        critical_parts=int(
            kpis["critical_parts"]
        ),
        high_risk_parts=int(
            kpis["high_risk_parts"]
        ),
        procurement_exposure_usd=float(
            kpis["procurement_value_usd"]
        ),
        settings=settings["readiness"],
    )

    refresh_time = (
        repository.load_database_refresh_time()
    )

    status_column, refresh_column = st.columns(
        [0.72, 0.28]
    )

    with status_column:
        message = (
            f"### {icon} Overall Spare-Parts Readiness: "
            f"{status}\n\n{explanation}"
        )

        if status == "Critical Attention":
            st.error(message)
        elif status == "Management Attention":
            st.warning(message)
        else:
            st.success(message)

    with refresh_column:
        st.info(
            "### Data refreshed\n\n"
            f"{refresh_time:%d %b %Y}\n\n"
            f"{refresh_time:%H:%M}"
        )


def render_kpis(
    repository: DashboardRepository,
) -> None:
    """Render Accountable Manager KPI cards."""

    kpis = repository.load_executive_kpis()

    first_row = st.columns(4)

    first_row[0].metric(
        "Forecast-active parts",
        f"{kpis['forecast_parts']:,}",
    )
    first_row[1].metric(
        "Critical stock risks",
        f"{kpis['critical_parts']:,}",
    )
    first_row[2].metric(
        "High stock risks",
        f"{kpis['high_risk_parts']:,}",
    )
    first_row[3].metric(
        "Procurement recommendations",
        f"{kpis['procurement_recommendations']:,}",
    )

    second_row = st.columns(4)

    second_row[0].metric(
        "Analysed inventory value",
        format_currency(
            kpis["inventory_value_usd"]
        ),
    )
    second_row[1].metric(
        "Projected procurement exposure",
        format_currency(
            kpis["procurement_value_usd"]
        ),
    )
    second_row[2].metric(
        "Recommended units",
        format_quantity(
            kpis["recommended_order_quantity"]
        ),
    )
    second_row[3].metric(
        "Assured AI advisories",
        f"{kpis['approved_advisories']:,}",
    )


def render_risk_and_finance(
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render stock-risk and procurement-exposure charts."""

    risk_summary = (
        repository.load_risk_summary()
    )

    chart_columns = st.columns(2)

    with chart_columns[0]:
        st.plotly_chart(
            create_risk_chart(
                risk_summary,
                settings["risk_order"],
                settings["risk_colours"],
            ),
            width="stretch",
        )

    with chart_columns[1]:
        st.plotly_chart(
            create_procurement_exposure_chart(
                risk_summary,
                settings["risk_order"],
                settings["risk_colours"],
            ),
            width="stretch",
        )


def render_confidence_and_advisories(
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render confidence and advisory-priority distributions."""

    confidence_data = (
        repository
        .load_forecast_confidence_summary()
    )

    advisory_data = (
        repository
        .load_advisory_priority_summary()
    )

    chart_columns = st.columns(2)

    with chart_columns[0]:
        st.plotly_chart(
            create_forecast_confidence_chart(
                confidence_data
            ),
            width="stretch",
        )

    with chart_columns[1]:
        st.plotly_chart(
            create_advisory_priority_chart(
                advisory_data,
                settings["risk_colours"],
            ),
            width="stretch",
        )


def render_model_selection(
    repository: DashboardRepository,
) -> None:
    """Render selected forecast-model distribution."""

    model_summary = (
        repository.load_model_summary()
    )

    if model_summary.empty:
        st.info(
            "No selected forecast-model results are available."
        )
        return

    st.plotly_chart(
        create_model_distribution_chart(
            model_summary
        ),
        width="stretch",
    )

    with st.expander(
        "View forecast-model performance summary"
    ):
        display_dataframe(
            model_summary,
            quantity_columns=[
                "part_count",
            ],
            height=260,
        )


def render_accountable_manager_advisories(
    repository: DashboardRepository,
    maximum_rows: int,
) -> None:
    """Render assured Accountable Manager recommendations."""

    recommendations = (
        repository.load_role_recommendations(
            "Accountable Manager",
            limit=maximum_rows,
        )
    )

    st.subheader(
        "Accountable Manager Advisory"
    )

    if recommendations.empty:
        st.success(
            "No Accountable Manager advisory exceptions "
            "are currently available."
        )
        return

    for row in recommendations.itertuples(
        index=False
    ):
        message = (
            f"**{row.priority} — {row.title}**\n\n"
            f"{row.recommendation}\n\n"
            f"**Rationale:** {row.rationale}\n\n"
            f"**Status:** {row.status}"
        )

        if row.priority == "Critical":
            st.error(message)
        elif row.priority == "High":
            st.warning(message)
        else:
            st.info(message)


def render_priority_actions(
    repository: DashboardRepository,
    maximum_rows: int,
) -> None:
    """Render the highest-priority procurement reviews."""

    st.subheader(
        "Highest-Priority Procurement Reviews"
    )

    recommendations = (
        repository.load_priority_recommendations(
            limit=maximum_rows,
        )
    )

    if recommendations.empty:
        st.success(
            "No current procurement recommendation "
            "requires action."
        )
        return

    display_dataframe(
        recommendations,
        currency_columns=[
            "procurement_value_usd",
        ],
        quantity_columns=[
            "current_balance",
            "recommended_order_quantity",
        ],
        height=500,
    )


def render_part_drilldown(
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render a consolidated spare-part management review."""

    if not bool(
        settings["drilldown"]["enabled"]
    ):
        return

    st.subheader(
        "Part-Level Management Drill-Down"
    )

    part_list = (
        repository.load_part_drilldown_list(
            limit=int(
                settings["drilldown"][
                    "maximum_parts"
                ]
            )
        )
    )

    if part_list.empty:
        st.info(
            "No part-level optimisation records are available."
        )
        return

    display_options = {
        (
            f"{row.part_number} — "
            f"{row.description} "
            f"[{row.stockout_risk}]"
        ): row.part_number
        for row in part_list.itertuples(
            index=False
        )
    }

    selected_label = st.selectbox(
        "Select a spare part",
        options=list(
            display_options.keys()
        ),
        key="executive_part_drilldown",
    )

    selected_part = display_options[
        selected_label
    ]

    details = repository.load_part_drilldown(
        selected_part
    )

    if details.empty:
        st.warning(
            "No detailed record was found for the selected part."
        )
        return

    row = details.iloc[0]

    first_row = st.columns(4)

    first_row[0].metric(
        "Current balance",
        format_quantity(
            row["current_balance"]
        ),
    )
    first_row[1].metric(
        "Reorder point",
        f"{float(row['reorder_point']):,.2f}",
    )
    first_row[2].metric(
        "12-month forecast",
        f"{float(row['forecast_12m']):,.2f}",
    )
    first_row[3].metric(
        "Recommended order",
        format_quantity(
            row["recommended_order_quantity"]
        ),
    )

    second_row = st.columns(4)

    second_row[0].metric(
        "Stockout risk",
        str(row["stockout_risk"]),
    )
    second_row[1].metric(
        "Forecast confidence",
        str(row["forecast_confidence"]),
    )
    second_row[2].metric(
        "Lead time",
        (
            f"{float(row['average_lead_time_days']):,.0f} "
            "days"
        ),
    )
    second_row[3].metric(
        "Procurement value",
        format_currency(
            row["procurement_value_usd"]
        ),
    )

    st.markdown(
        "**Selected forecast model:** "
        f"`{row['selected_forecast_model']}`"
    )

    st.markdown(
        "**Optimisation rationale:** "
        f"{row['recommendation_reason']}"
    )

    advisories = repository.load_part_advisories(
        selected_part
    )

    with st.expander(
        "View cross-functional agent advisories"
    ):
        if advisories.empty:
            st.info(
                "No assured part-level advisory is available."
            )
        else:
            for advisory in advisories.itertuples(
                index=False
            ):
                st.markdown(
                    f"### {advisory.priority} — "
                    f"{advisory.target_role}"
                )
                st.write(
                    advisory.recommendation
                )
                st.caption(
                    f"Rationale: {advisory.rationale}"
                )
                st.divider()


def render_data_status(
    repository: DashboardRepository,
) -> None:
    """Render source-table availability."""

    with st.expander(
        "Data and pipeline status"
    ):
        status = repository.load_data_status()

        available_count = int(
            (
                status["status"]
                == "Available"
            ).sum()
        )

        st.write(
            f"{available_count} of {len(status)} "
            "dashboard source tables are available."
        )

        display_dataframe(
            status,
            quantity_columns=[
                "row_count",
            ],
            height=420,
        )


def render_executive_dashboard(
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render the Accountable Manager dashboard."""

    st.title(
        "Accountable Manager Dashboard"
    )

    st.caption(
        "Enterprise inventory risk, procurement exposure, "
        "forecasting status and assured management advisories."
    )

    render_readiness_header(
        repository,
        settings,
    )

    render_kpis(
        repository
    )

    st.divider()

    render_risk_and_finance(
        repository,
        settings,
    )

    st.divider()

    render_confidence_and_advisories(
        repository,
        settings,
    )

    st.divider()

    model_column, advisory_column = st.columns(
        [1.1, 0.9]
    )

    with model_column:
        render_model_selection(
            repository
        )

    with advisory_column:
        render_accountable_manager_advisories(
            repository,
            maximum_rows=int(
                settings["display"][
                    "top_recommendations"
                ]
            ),
        )

    st.divider()

    render_priority_actions(
        repository,
        maximum_rows=int(
            settings["display"][
                "top_recommendations"
            ]
        ),
    )

    st.divider()

    render_part_drilldown(
        repository,
        settings,
    )

    render_data_status(
        repository
    )