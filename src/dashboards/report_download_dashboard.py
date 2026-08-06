"""Management-report generation and download dashboard."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from src.dashboards.dashboard_utils import (
    determine_pipeline_freshness,
)
from src.dashboards.data_access import (
    DashboardRepository,
)
from src.reporting.management_report import (
    generate_management_report,
)


REPORT_BYTES_KEY = "management_report_bytes"
REPORT_NAME_KEY = "management_report_filename"
REPORT_TIME_KEY = "management_report_generated_at"
REPORT_PIPELINE_KEY = "management_report_pipeline_run_id"


def create_download_filename(
    base_filename: str,
    generated_at: datetime,
) -> str:
    """Create a timestamped Excel download filename."""

    base_path = Path(base_filename)

    stem = base_path.stem
    suffix = base_path.suffix or ".xlsx"

    timestamp = generated_at.strftime(
        "%Y%m%d_%H%M%S"
    )

    return f"{stem}_{timestamp}{suffix}"


def read_report_bytes(
    report_path: Path,
) -> bytes:
    """Read a generated report into memory."""

    if not report_path.is_file():
        raise FileNotFoundError(
            f"Generated report was not found: {report_path}"
        )

    return report_path.read_bytes()


def clear_cached_report() -> None:
    """Remove the generated report from session state."""

    keys = [
        REPORT_BYTES_KEY,
        REPORT_NAME_KEY,
        REPORT_TIME_KEY,
        REPORT_PIPELINE_KEY,
    ]

    for key in keys:
        st.session_state.pop(
            key,
            None,
        )


def render_pipeline_information(
    repository: DashboardRepository,
    *,
    stale_after_hours: float,
) -> dict[str, Any]:
    """Display the latest pipeline information."""

    pipeline_kpis = (
        repository.load_pipeline_kpis()
    )

    freshness_status, age_hours = (
        determine_pipeline_freshness(
            completed_at=pipeline_kpis[
                "completed_at"
            ],
            stale_after_hours=(
                stale_after_hours
            ),
        )
    )

    columns = st.columns(4)

    columns[0].metric(
        "Pipeline status",
        str(
            pipeline_kpis[
                "overall_status"
            ]
        ),
    )

    successful_stage_count = int(
        pipeline_kpis[
            "successful_stage_count"
        ]
    )

    columns[1].metric(
        "Successful stages",
        f"{successful_stage_count:,}",
    )

    columns[2].metric(
        "Data freshness",
        freshness_status,
    )

    columns[3].metric(
        "Data age",
        f"{age_hours:.2f} hours",
    )

    pipeline_run_id = (
        pipeline_kpis[
            "pipeline_run_id"
        ]
    )

    if pipeline_run_id:
        st.caption(
            "Latest pipeline run ID: "
            f"`{pipeline_run_id}`"
        )

    return {
        **pipeline_kpis,
        "freshness_status": (
            freshness_status
        ),
        "age_hours": age_hours,
    }


def generate_report_for_download(
    *,
    repository: DashboardRepository,
    database_path: Path,
    reports_directory: Path,
    report_settings: dict[str, Any],
    pipeline_run_id: str | None,
) -> None:
    """Generate and store the report in session state."""

    generated_at = datetime.now()

    output_filename = str(
        report_settings[
            "output_filename"
        ]
    )

    output_path = (
        reports_directory
        / output_filename
    )

    generated_path = (
        generate_management_report(
            repository=repository,
            database_path=database_path,
            output_path=output_path,
            report_settings=report_settings,
        )
    )

    report_bytes = read_report_bytes(
        generated_path
    )

    download_filename = (
        create_download_filename(
            output_filename,
            generated_at,
        )
    )

    st.session_state[
        REPORT_BYTES_KEY
    ] = report_bytes

    st.session_state[
        REPORT_NAME_KEY
    ] = download_filename

    st.session_state[
        REPORT_TIME_KEY
    ] = generated_at.isoformat(
        timespec="seconds"
    )

    st.session_state[
        REPORT_PIPELINE_KEY
    ] = pipeline_run_id


def render_generated_report_status() -> None:
    """Display information about the generated report."""

    report_bytes = st.session_state.get(
        REPORT_BYTES_KEY
    )

    if not report_bytes:
        st.info(
            "No report has been generated during "
            "this application session."
        )
        return

    filename = st.session_state.get(
        REPORT_NAME_KEY,
        "aviation_spare_parts_management_report.xlsx",
    )

    generated_at = st.session_state.get(
        REPORT_TIME_KEY,
        "Unavailable",
    )

    pipeline_run_id = st.session_state.get(
        REPORT_PIPELINE_KEY
    )

    report_size_kb = (
        len(report_bytes)
        / 1024
    )

    st.success(
        "The management report is ready for download."
    )

    details = st.columns(3)

    details[0].metric(
        "Report size",
        f"{report_size_kb:,.1f} KB",
    )

    details[1].metric(
        "Generated at",
        str(generated_at),
    )

    details[2].metric(
        "Pipeline run",
        str(
            pipeline_run_id
            or "Unavailable"
        ),
    )

    st.download_button(
        label="Download Management Report",
        data=report_bytes,
        file_name=str(filename),
        mime=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        width="stretch",
        type="primary",
        key="download_management_report",
    )


def render_report_download_dashboard(
    *,
    repository: DashboardRepository,
    database_path: Path,
    reports_directory: Path,
    report_settings: dict[str, Any],
    download_settings: dict[str, Any],
) -> None:
    """Render the management-report download dashboard."""

    st.title(
        "Management Report Download"
    )

    st.caption(
        "Generate and download the latest read-only "
        "aviation spare-parts management report."
    )

    if not bool(
        download_settings["enabled"]
    ):
        st.warning(
            "Dashboard report download is disabled "
            "in the project settings."
        )
        return

    pipeline_information = (
        render_pipeline_information(
            repository,
            stale_after_hours=float(
                download_settings[
                    "stale_after_hours"
                ]
            ),
        )
    )

    pipeline_status = str(
        pipeline_information[
            "overall_status"
        ]
    )

    freshness_status = str(
        pipeline_information[
            "freshness_status"
        ]
    )

    pipeline_run_id = (
        pipeline_information[
            "pipeline_run_id"
        ]
    )

    require_successful_pipeline = bool(
        download_settings[
            "require_successful_pipeline"
        ]
    )

    generation_allowed = not (
        require_successful_pipeline
        and pipeline_status != "Passed"
    )

    if not generation_allowed:
        st.error(
            "Report generation is unavailable because "
            "the latest pipeline run did not pass."
        )

    elif (
        freshness_status == "Stale"
        and bool(
            download_settings[
                "warn_when_stale"
            ]
        )
    ):
        st.warning(
            "The latest pipeline data is stale. "
            "Run the full pipeline before generating "
            "a management report where possible."
        )

    st.divider()

    st.subheader(
        "Report Contents"
    )

    st.markdown(
        """
        The Excel workbook includes:

        - Executive Summary
        - Procurement Review
        - Finance Exposure
        - Engineering Review
        - Operations Readiness
        - Quality Assurance
        - Pipeline Audit
        - Report Metadata
        """
    )

    st.info(
        "The report is decision support only. "
        "It cannot create purchase orders, update inventory, "
        "approve expenditure or replace authorised review."
    )

    action_columns = st.columns(
        [0.75, 0.25]
    )

    generate_clicked = (
        action_columns[0].button(
            str(
                download_settings[
                    "generate_label"
                ]
            ),
            type="primary",
            width="stretch",
            disabled=not generation_allowed,
            key="generate_management_report",
        )
    )

    clear_clicked = (
        action_columns[1].button(
            "Clear Generated Report",
            width="stretch",
            key="clear_management_report",
        )
    )

    if clear_clicked:
        clear_cached_report()
        st.rerun()

    if generate_clicked:
        try:
            with st.spinner(
                "Generating the latest Excel "
                "management report..."
            ):
                generate_report_for_download(
                    repository=repository,
                    database_path=database_path,
                    reports_directory=(
                        reports_directory
                    ),
                    report_settings=(
                        report_settings
                    ),
                    pipeline_run_id=(
                        str(pipeline_run_id)
                        if pipeline_run_id
                        else None
                    ),
                )

        except Exception as exc:
            clear_cached_report()

            st.error(
                "Management-report generation failed: "
                f"{exc}"
            )

    st.divider()

    render_generated_report_status()