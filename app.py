"""Streamlit entry point for the aviation spare-parts platform."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.dashboards.engineering_dashboard import (
    render_engineering_dashboard,
)
from src.dashboards.finance_dashboard import (
    render_finance_dashboard,
)
from src.dashboards.operations_dashboard import (
    render_operations_dashboard,
)
from src.dashboards.procurement_dashboard import (
    render_procurement_dashboard,
)
from src.dashboards.quality_dashboard import (
    render_quality_dashboard,
)
from src.dashboards.pipeline_dashboard import (
    render_pipeline_dashboard,
)

from src.dashboards.report_download_dashboard import (
    render_report_download_dashboard,
)

from src.dashboards.data_access import (
    DashboardDataError,
    DashboardRepository,
)
from src.dashboards.executive_dashboard import (
    render_executive_dashboard,
)

from src.dashboards.dashboard_utils import (
    apply_dashboard_styling,
)

import streamlit as st
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent


def load_settings() -> dict[str, Any]:
    """Load application settings."""

    settings_path = (
        PROJECT_ROOT
        / "config"
        / "settings.yaml"
    )

    with settings_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        settings = yaml.safe_load(file)

    if not isinstance(settings, dict):
        raise ValueError(
            "Project settings must be a YAML mapping."
        )

    return settings


def configure_page(
    dashboard_settings: dict[str, Any],
) -> None:
    """Configure the Streamlit page."""

    st.set_page_config(
        page_title=dashboard_settings["title"],
        page_icon="✈️",
        layout=dashboard_settings["page"][
            "layout"
        ],
        initial_sidebar_state=(
            dashboard_settings["page"][
                "sidebar_state"
            ]
        ),
    )


def render_sidebar() -> str:
    """Render dashboard navigation."""

    st.sidebar.title(
        "Aviation Spare Parts"
    )

    st.sidebar.caption(
        "Forecasting and agentic decision support"
    )

    selected_page = st.sidebar.radio(
    "Management view",
    options=[
        "Accountable Manager",
        "Procurement Manager",
        "Finance Manager",
        "Engineering Manager",
        "Operations Manager",
        "Quality Manager",
        "Pipeline Monitor",
        "Management Report",
    ],
    index=0,
    key="management_view_navigation",
)

    st.sidebar.divider()

    st.sidebar.markdown(
        "**System status**"
    )

    st.sidebar.success(
        "Read-only decision support"
    )

    st.sidebar.info(
        "Human approval required"
    )

    st.sidebar.divider()

    st.sidebar.markdown(
        "**Governance controls**"
    )

    st.sidebar.info(
        "✓ No automatic purchasing"
    )

    st.sidebar.info(
        "✓ No inventory write-back"
    )

    st.sidebar.caption(
        "All management views use validated analytics and "
        "assured recommendations. Forecasts, optimisation "
        "outputs and AI recommendations must be reviewed by "
        "authorised personnel."
    )

    return selected_page


def main() -> None:
    """Run the Streamlit application."""

    settings = load_settings()

    dashboard_settings = settings[
        "dashboard"
    ]

    configure_page(
        dashboard_settings
    )

    apply_dashboard_styling()

    selected_page = render_sidebar()

    database_path = (
        PROJECT_ROOT
        / settings["paths"]["database"]
    )

    reports_directory = (
        PROJECT_ROOT
        / settings["paths"]["reports"]
    )

    audit_database_path = (
        PROJECT_ROOT
        / settings["paths"][
            "management_audit_database"
        ]
    )

    try:
        repository = DashboardRepository(
            database_path
        )

        if selected_page == "Accountable Manager":
            render_executive_dashboard(
                repository,
                dashboard_settings,
                audit_database_path,
            )

        elif selected_page == "Procurement Manager":
            render_procurement_dashboard(
                repository,
                dashboard_settings,
                audit_database_path,
            )

        elif selected_page == "Finance Manager":
            render_finance_dashboard(
                repository,
                dashboard_settings,
                audit_database_path,
            )

        elif selected_page == "Engineering Manager":
            render_engineering_dashboard(
                repository,
                dashboard_settings,
                audit_database_path,
            )

        elif selected_page == "Operations Manager":
            render_operations_dashboard(
                repository,
                dashboard_settings,
                audit_database_path,
            )

        elif selected_page == "Quality Manager":
            render_quality_dashboard(
                repository,
                dashboard_settings,
                audit_database_path,
            )

        elif selected_page == "Pipeline Monitor":
            render_pipeline_dashboard(
                repository,
                dashboard_settings,
                project_root=PROJECT_ROOT,
                reports_directory=reports_directory,
                scheduling_settings=settings[
                    "scheduling"
                ],
            )

        elif selected_page == "Management Report":
            render_report_download_dashboard(
                repository=repository,
                database_path=database_path,
                reports_directory=reports_directory,
                report_settings=settings[
                    "reporting"
                ][
                    "management_report"
                ],
                download_settings=dashboard_settings[
                    "report_download"
                ],
            )

    except DashboardDataError as exc:
        st.error(
            f"Dashboard failed to start: {exc}"
        )

    except Exception as exc:
        st.error(
            f"Unexpected application error: {exc}"
        )


if __name__ == "__main__":
    main()