"""Reusable forecast explainability dashboard component."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboards.dashboard_utils import (
    display_dataframe,
)
from src.dashboards.data_access import (
    DashboardRepository,
)
from src.forecasting.explainability import (
    build_forecast_explanation,
)


def _format_metric(
    value: object,
    *,
    decimals: int = 4,
) -> str:
    """Safely format an analytical metric."""

    if value is None:
        return "N/A"

    try:
        if pd.isna(value):
            return "N/A"
    except (
        TypeError,
        ValueError,
    ):
        pass

    try:
        numeric_value = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return str(value)

    return (
        f"{numeric_value:,.{decimals}f}"
    )


def _format_integer(
    value: object,
) -> str:
    """Safely format an integer metric."""

    if value is None:
        return "N/A"

    try:
        if pd.isna(value):
            return "N/A"
    except (
        TypeError,
        ValueError,
    ):
        pass

    try:
        return f"{int(value):,}"
    except (
        TypeError,
        ValueError,
    ):
        return str(value)


def render_forecast_explainability(
    *,
    repository: DashboardRepository,
    part_number: str,
) -> None:
    """Render deterministic forecast explainability."""

    st.markdown(
        "### Forecast Explainability"
    )

    selected_model_record = (
        repository
        .load_selected_forecast_model(
            part_number
        )
    )

    demand_record = (
        repository
        .load_part_demand_metrics(
            part_number
        )
    )

    if not selected_model_record:
        st.info(
            "No selected forecast-model evidence "
            "is available for this spare part."
        )
        return

    explanation = (
        build_forecast_explanation(
            selected_model_record=(
                selected_model_record
            ),
            demand_record=demand_record,
        )
    )

    selected_model = (
        explanation.get(
            "selected_model"
        )
        or "Unavailable"
    )

    forecast_confidence = (
        explanation.get(
            "forecast_confidence"
        )
        or "Unavailable"
    )

    demand_pattern = (
        explanation.get(
            "demand_pattern"
        )
        or "Unavailable"
    )

    selection_metric = (
        explanation.get(
            "selection_metric"
        )
        or "Unavailable"
    )

    selection_score = (
        explanation.get(
            "selection_score"
        )
    )

    successful_model_count = (
        explanation.get(
            "successful_model_count"
        )
    )

    first_row = st.columns(5)

    first_row[0].metric(
        "Selected model",
        str(selected_model),
    )

    first_row[1].metric(
        "Forecast confidence",
        str(forecast_confidence),
    )

    first_row[2].metric(
        "Demand pattern",
        str(demand_pattern),
    )

    first_row[3].metric(
        "Selection metric",
        str(selection_metric).upper(),
    )

    first_row[4].metric(
        "Selection score",
        _format_metric(
            selection_score,
            decimals=4,
        ),
    )

    st.markdown(
        "**Why was this model selected?**"
    )

    selection_reason = (
        explanation.get(
            "selection_reason"
        )
        or (
            "No stored model-selection "
            "reason is available."
        )
    )

    st.info(
        str(selection_reason)
    )

    st.markdown(
        "**Why this confidence level?**"
    )

    st.write(
        explanation[
            "confidence_explanation"
        ]
    )

    if demand_record:
        evidence_columns = st.columns(5)

        evidence_columns[0].metric(
            "History months",
            _format_integer(
                demand_record.get(
                    "history_months"
                )
            ),
        )

        evidence_columns[1].metric(
            "Active demand months",
            _format_integer(
                demand_record.get(
                    "active_demand_months"
                )
            ),
        )

        evidence_columns[2].metric(
            "Zero-demand months",
            _format_integer(
                demand_record.get(
                    "zero_demand_months"
                )
            ),
        )

        evidence_columns[3].metric(
            "ADI",
            _format_metric(
                demand_record.get(
                    "adi"
                ),
                decimals=2,
            ),
        )

        evidence_columns[4].metric(
            "CV²",
            _format_metric(
                demand_record.get(
                    "cv_squared"
                ),
                decimals=4,
            ),
        )

    st.markdown(
        "**Management interpretation**"
    )

    st.warning(
        explanation[
            "management_interpretation"
        ]
    )

    successful_models_display = (
        _format_integer(
            successful_model_count
        )
    )

    st.caption(
        "Successful candidate models evaluated: "
        f"{successful_models_display}"
    )

    backtest_results = (
        repository
        .load_forecast_backtest_results(
            part_number
        )
    )

    with st.expander(
        "View candidate-model comparison"
    ):
        if backtest_results.empty:
            st.info(
                "No forecast backtesting records "
                "are available."
            )
        else:
            display_dataframe(
                backtest_results,
                height=320,
            )

    st.caption(
        explanation[
            "governance_statement"
        ]
    )