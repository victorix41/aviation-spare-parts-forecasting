"""Pipeline status and audit-monitoring dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboards.dashboard_utils import (
    create_pipeline_history_chart,
    create_pipeline_stage_chart,
    determine_pipeline_freshness,
    display_dataframe,
)
from src.dashboards.data_access import (
    DashboardRepository,
)


def render_pipeline_status_banner(
    *,
    overall_status: str,
    freshness_status: str,
    age_hours: float,
) -> None:
    """Render overall pipeline health."""

    message = (
        f"Latest pipeline status: {overall_status}. "
        f"Data age: {age_hours:.2f} hours."
    )

    if overall_status == "Failed":
        st.error(
            message
        )
        return

    if freshness_status == "Stale":
        st.warning(
            message
        )
        return

    if overall_status == "Passed":
        st.success(
            message
        )
        return

    st.info(
        message
    )


def render_pipeline_dashboard(
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render the complete pipeline-monitoring dashboard."""

    st.title(
        "Pipeline Status and Audit Monitoring"
    )

    st.caption(
        "End-to-end processing status, execution history, "
        "data freshness and pipeline audit records."
    )

    monitoring_settings = settings[
        "pipeline_monitoring"
    ]

    kpis = repository.load_pipeline_kpis()

    freshness_status, age_hours = (
        determine_pipeline_freshness(
            completed_at=kpis["completed_at"],
            stale_after_hours=float(
                monitoring_settings[
                    "stale_after_hours"
                ]
            ),
        )
    )

    render_pipeline_status_banner(
        overall_status=str(
            kpis["overall_status"]
        ),
        freshness_status=(
            freshness_status
        ),
        age_hours=age_hours,
    )

    first_row = st.columns(4)

    first_row[0].metric(
        "Latest status",
        str(
            kpis["overall_status"]
        ),
    )

    first_row[1].metric(
        "Successful stages",
        f"{kpis['successful_stage_count']:,}",
    )

    first_row[2].metric(
        "Failed stages",
        f"{kpis['failed_stage_count']:,}",
    )

    first_row[3].metric(
        "Pipeline duration",
        f"{float(kpis['duration_seconds']):.2f}s",
    )

    second_row = st.columns(4)

    second_row[0].metric(
        "Data freshness",
        freshness_status,
    )

    second_row[1].metric(
        "Data age",
        f"{age_hours:.2f} hours",
    )

    second_row[2].metric(
        "Slowest stage",
        str(
            kpis["slowest_stage"]
            or "Unavailable"
        ),
    )

    slowest_stage_seconds = float(
        kpis["slowest_stage_seconds"]
    )

    second_row[3].metric(
        "Slowest-stage duration",
        f"{slowest_stage_seconds:.2f} s",
    )

    if kpis["pipeline_run_id"]:
        st.caption(
            "Latest pipeline run ID: "
            f"`{kpis['pipeline_run_id']}`"
        )

    st.divider()

    latest_stages = (
        repository
        .load_latest_pipeline_stages()
    )

    if latest_stages.empty:
        st.warning(
            "No pipeline-stage audit records are available."
        )
    else:
        st.plotly_chart(
            create_pipeline_stage_chart(
                latest_stages,
                monitoring_settings[
                    "status_colours"
                ],
            ),
            width="stretch",
        )

        st.subheader(
            "Latest Pipeline Stage Audit"
        )

        display_dataframe(
            latest_stages,
            height=360,
        )

    st.divider()

    recent_runs = (
        repository.load_recent_pipeline_runs(
            limit=int(
                monitoring_settings[
                    "recent_run_limit"
                ]
            )
        )
    )

    if recent_runs.empty:
        st.info(
            "No recent pipeline-run history is available."
        )
    else:
        st.plotly_chart(
            create_pipeline_history_chart(
                recent_runs,
                monitoring_settings[
                    "status_colours"
                ],
            ),
            width="stretch",
        )

        st.subheader(
            "Recent Pipeline Runs"
        )

        display_dataframe(
            recent_runs,
            height=360,
        )

    st.divider()

    st.subheader(
        "Pipeline Table Availability"
    )

    table_status = (
        repository
        .load_pipeline_table_status()
    )

    missing_count = int(
        (
            table_status["status"]
            == "Missing"
        ).sum()
    )

    empty_count = int(
        (
            table_status["status"]
            == "Empty"
        ).sum()
    )

    status_columns = st.columns(3)

    status_columns[0].metric(
        "Tables checked",
        f"{len(table_status):,}",
    )

    status_columns[1].metric(
        "Missing tables",
        f"{missing_count:,}",
    )

    status_columns[2].metric(
        "Empty tables",
        f"{empty_count:,}",
    )

    if missing_count > 0:
        st.error(
            "One or more required pipeline tables are missing."
        )
    elif empty_count > 0:
        st.warning(
            "One or more pipeline tables are available but empty."
        )
    else:
        st.success(
            "All monitored pipeline tables are available "
            "and contain records."
        )

    display_dataframe(
        table_status,
        quantity_columns=[
            "row_count",
        ],
        height=500,
    )

    failed_stages = (
        latest_stages.loc[
            latest_stages["status"]
            == "Failed"
        ]
        if not latest_stages.empty
        else pd.DataFrame()
    )

    if not failed_stages.empty:
        st.divider()

        st.subheader(
            "Failure Details"
        )

        for row in failed_stages.itertuples(
            index=False
        ):
            st.error(
                f"**{row.stage_name}**\n\n"
                f"Module: `{row.module_name}`\n\n"
                f"Return code: {row.return_code}\n\n"
                f"Error: {row.error_message}"
            )