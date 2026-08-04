"""Main Streamlit entry point for the aviation spare-parts project."""

from __future__ import annotations

import streamlit as st


def configure_page() -> None:
    """Configure the Streamlit browser page."""

    st.set_page_config(
        page_title="Aviation Spare Parts Forecasting",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_header() -> None:
    """Render the application heading and project status."""

    st.title("Aviation Spare Parts Demand Forecasting")
    st.subheader("Inventory Optimisation and Agentic AI Decision Support")

    st.info(
        "Phase 1: Project foundation completed. "
        "Data ingestion and validation will be implemented in the next phase."
    )


def render_governance_notice() -> None:
    """Display the mandatory human-approval notice."""

    st.warning(
        "AI and forecasting outputs are decision-support recommendations only. "
        "No purchase order may be issued without authorised human review and approval."
    )


def main() -> None:
    """Run the Streamlit application."""

    configure_page()
    render_header()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Project Phase", "1 of 16")

    with col2:
        st.metric("Data Status", "Not loaded")

    with col3:
        st.metric("Forecast Status", "Not started")

    render_governance_notice()


if __name__ == "__main__":
    main()