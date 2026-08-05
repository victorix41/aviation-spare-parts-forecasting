"""Streamlit entry point for the aviation spare-parts platform."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from src.dashboards.data_access import (
    DashboardDataError,
    DashboardRepository,
)
from src.dashboards.executive_dashboard import (
    render_executive_dashboard,
)


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
        ],
        index=0,
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

    st.sidebar.caption(
        "Phase 3.6A currently implements the "
        "Accountable Manager view. The remaining role "
        "dashboards will be added in Phase 3.6B."
    )

    return selected_page


def render_placeholder(
    role_name: str,
) -> None:
    """Render a temporary role-page placeholder."""

    st.title(
        f"{role_name} Dashboard"
    )

    st.info(
        f"The {role_name} view will be implemented "
        "in Phase 3.6B. Use the Accountable Manager "
        "view to confirm the shared dashboard framework."
    )


def main() -> None:
    """Run the management dashboard."""

    try:
        settings = load_settings()

        dashboard_settings = settings[
            "dashboard"
        ]

        configure_page(
            dashboard_settings
        )

        database_path = (
            PROJECT_ROOT
            / settings["paths"]["database"]
        )

        repository = DashboardRepository(
            database_path
        )

        selected_page = render_sidebar()

        if selected_page == "Accountable Manager":
            render_executive_dashboard(
                repository,
                dashboard_settings,
            )
        else:
            render_placeholder(
                selected_page
            )

    except DashboardDataError as exc:
        st.error(
            str(exc)
        )

        st.code(
            "\n".join(
                [
                    "python -m src.data.ingestion_pipeline",
                    "python -m src.analytics.run_demand_analysis",
                    "python -m src.forecasting.run_model_selection",
                    "python -m src.optimisation.run_inventory_optimisation",
                    "python -m src.agents.run_advisory_engine",
                ]
            ),
            language="bash",
        )

    except Exception as exc:
        st.error(
            f"Dashboard failed to start: {exc}"
        )


if __name__ == "__main__":
    main()