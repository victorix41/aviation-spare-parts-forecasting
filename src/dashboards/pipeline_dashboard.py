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

from pathlib import Path

from src.scheduling.job_monitoring import (
    determine_scheduled_job_freshness,
    inspect_job_lock,
    load_recent_job_logs,
    load_scheduled_job_summary,
    read_job_log,
    scheduled_job_stages_frame,
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

def render_scheduled_job_monitoring(
    *,
    project_root: Path,
    scheduling_settings: dict,
) -> None:
    """Render scheduled pipeline and report monitoring."""

    st.subheader(
        "Scheduled Pipeline and Report Execution"
    )

    summary_path = (
        project_root
        / scheduling_settings[
            "latest_summary"
        ]
    )

    log_directory = (
        project_root
        / scheduling_settings[
            "log_directory"
        ]
    )

    lock_path = (
        project_root
        / scheduling_settings[
            "lock_file"
        ]
    )

    monitoring_settings = (
        scheduling_settings[
            "monitoring"
        ]
    )

    summary = load_scheduled_job_summary(
        summary_path
    )

    if summary is None:
        st.info(
            "No scheduled-job execution summary "
            "is currently available."
        )

    else:
        freshness_status, age_hours = (
            determine_scheduled_job_freshness(
                completed_at=summary.get(
                    "completed_at"
                ),
                stale_after_hours=float(
                    monitoring_settings[
                        "stale_after_hours"
                    ]
                ),
            )
        )

        overall_status = str(
            summary.get(
                "overall_status",
                "Unknown",
            )
        )

        job_run_id = str(
            summary.get(
                "job_run_id",
                "Unavailable",
            )
        )

        duration_seconds = float(
            summary.get(
                "duration_seconds",
                0.0,
            )
            or 0.0
        )

        stages = scheduled_job_stages_frame(
            summary
        )

        passed_stage_count = int(
            (
                stages["status"]
                == "Passed"
            ).sum()
        )

        failed_stage_count = int(
            (
                stages["status"]
                == "Failed"
            ).sum()
        )

        if overall_status == "Failed":
            st.error(
                "The latest scheduled execution failed."
            )

        elif freshness_status == "Stale":
            st.warning(
                "The latest scheduled execution passed, "
                "but its result is stale."
            )

        else:
            st.success(
                "The latest scheduled execution passed."
            )

        metric_columns = st.columns(6)

        metric_columns[0].metric(
            "Scheduled status",
            overall_status,
        )

        metric_columns[1].metric(
            "Stages passed",
            f"{passed_stage_count:,}",
        )

        metric_columns[2].metric(
            "Stages failed",
            f"{failed_stage_count:,}",
        )

        metric_columns[3].metric(
            "Job duration",
            f"{duration_seconds:.2f} s",
        )

        metric_columns[4].metric(
            "Result freshness",
            freshness_status,
        )

        metric_columns[5].metric(
            "Result age",
            f"{age_hours:.2f} hours",
        )

        st.caption(
            "Latest scheduled-job run ID: "
            f"`{job_run_id}`"
        )

        if not stages.empty:
            st.markdown(
                "**Scheduled workflow stages**"
            )

            display_dataframe(
                stages[
                    [
                        "module_name",
                        "status",
                        "return_code",
                        "started_at",
                        "completed_at",
                        "duration_seconds",
                    ]
                ],
                height=220,
            )

        error_message = summary.get(
            "error_message"
        )

        if error_message:
            st.error(
                f"Scheduled-job error: {error_message}"
            )

    st.markdown(
        "**Job lock status**"
    )

    lock_status = inspect_job_lock(
        lock_path,
        stale_after_minutes=float(
            monitoring_settings[
                "stale_lock_after_minutes"
            ]
        ),
    )

    lock_columns = st.columns(3)

    lock_columns[0].metric(
        "Lock file",
        str(
            lock_status["status"]
        ),
    )

    lock_age_minutes = float(
        lock_status["age_minutes"]
    )

    lock_columns[1].metric(
        "Lock age",
        f"{lock_age_minutes:.2f} minutes",
    )

    lock_columns[2].metric(
        "Process ID",
        str(
            lock_status["process_id"]
            or "Unavailable"
        ),
    )

    if lock_status["status"] == "Stale":
        st.error(
            "A stale scheduled-job lock file exists. "
            "Verify that no job is running before removing it."
        )

    recent_logs = load_recent_job_logs(
        log_directory,
        limit=int(
            monitoring_settings[
                "recent_log_limit"
            ]
        ),
    )

    st.markdown(
        "**Recent scheduled-job logs**"
    )

    if recent_logs.empty:
        st.info(
            "No scheduled-job logs are available."
        )

    else:
        display_dataframe(
            recent_logs[
                [
                    "log_filename",
                    "modified_at",
                    "size_bytes",
                ]
            ],
            quantity_columns=[
                "size_bytes",
            ],
            height=280,
        )

        selected_log = st.selectbox(
            "View scheduled-job log",
            options=recent_logs[
                "log_filename"
            ].tolist(),
            key="scheduled_job_log_selection",
        )

        selected_row = recent_logs.loc[
            recent_logs[
                "log_filename"
            ]
            == selected_log
        ].iloc[0]

        log_content = read_job_log(
            Path(
                selected_row[
                    "log_path"
                ]
            )
        )

        with st.expander(
            "Open selected scheduled-job log"
        ):
            st.code(
                log_content,
                language="text",
            )


def render_pipeline_dashboard(
    repository: DashboardRepository,
    settings: dict,
    *,
    project_root: Path,
    scheduling_settings: dict,
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

    st.divider()

    render_scheduled_job_monitoring(    
        project_root=project_root,
        scheduling_settings=scheduling_settings,
    )