"""Management-facing data-quality monitoring."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.dashboards.data_access import (
    DashboardRepository,
)
from src.validation.data_quality_monitoring import (
    check_data_staleness,
    check_duplicate_keys,
    check_future_dates,
    check_negative_values,
    check_required_columns,
    check_required_values,
    summarise_data_quality,
)


def render_data_quality_monitoring(
    *,
    repository: DashboardRepository,
    settings: dict,
) -> None:
    """Render deterministic data-quality monitoring."""

    monitoring_settings = (
        settings.get(
            "data_quality_monitoring",
            {},
        )
    )

    if not bool(
        monitoring_settings.get(
            "enabled",
            True,
        )
    ):
        return

    st.markdown(
        "### Data Quality Monitoring"
    )

    datasets = {
        "inventory": (
            repository
            .load_data_quality_inventory()
        ),
        "issue_history": (
            repository
            .load_data_quality_issue_history()
        ),
        "repair_orders": (
            repository
            .load_data_quality_repair_orders()
        ),
    }

    findings = []

    required_fields = (
        monitoring_settings.get(
            "required_fields",
            {},
        )
    )

    duplicate_keys = (
        monitoring_settings.get(
            "duplicate_keys",
            {},
        )
    )

    non_negative_fields = (
        monitoring_settings.get(
            "non_negative_fields",
            {},
        )
    )

    date_fields = (
        monitoring_settings.get(
            "date_fields",
            {},
        )
    )

    for dataset_name, dataframe in datasets.items():
        required = required_fields.get(
            dataset_name,
            [],
        )

        findings.extend(
            check_required_columns(
                dataframe=dataframe,
                dataset=dataset_name,
                required_columns=required,
            )
        )

        findings.extend(
            check_required_values(
                dataframe=dataframe,
                dataset=dataset_name,
                required_columns=required,
            )
        )

        findings.extend(
            check_duplicate_keys(
                dataframe=dataframe,
                dataset=dataset_name,
                key_columns=duplicate_keys.get(
                    dataset_name,
                    [],
                ),
            )
        )

        findings.extend(
            check_negative_values(
                dataframe=dataframe,
                dataset=dataset_name,
                numeric_columns=(
                    non_negative_fields.get(
                        dataset_name,
                        [],
                    )
                ),
            )
        )

        findings.extend(
            check_future_dates(
                dataframe=dataframe,
                dataset=dataset_name,
                date_columns=date_fields.get(
                    dataset_name,
                    [],
                ),
            )
        )

    # -------------------------------------------------
    # Freshness monitoring
    # -------------------------------------------------

    freshness_settings = (
        monitoring_settings.get(
            "freshness",
            {},
        )
    )

    for dataset_name, freshness_rule in (
        freshness_settings.items()
    ):
        if dataset_name not in datasets:
            continue

        date_field = freshness_rule.get(
            "date_field"
        )

        stale_after_days = int(
            freshness_rule.get(
                "stale_after_days",
                45,
            )
        )

        if not date_field:
            continue

        findings.extend(
            check_data_staleness(
                dataframe=datasets[
                    dataset_name
                ],
                dataset=dataset_name,
                date_column=date_field,
                reference_date=datetime.now(
                    timezone.utc
                ),
                stale_after_days=(
                    stale_after_days
                ),
            )
        )

    # -------------------------------------------------
    # Summarise all findings
    # -------------------------------------------------

    summary = summarise_data_quality(
        findings
    )

    metric_columns = st.columns(5)

    metric_columns[0].metric(
        "Data-quality status",
        str(
            summary[
                "status"
            ]
        ),
    )

    metric_columns[1].metric(
        "Total findings",
        int(
            summary[
                "total_findings"
            ]
        ),
    )

    metric_columns[2].metric(
        "Critical",
        int(
            summary[
                "critical_findings"
            ]
        ),
    )

    metric_columns[3].metric(
        "High",
        int(
            summary[
                "high_findings"
            ]
        ),
    )

    metric_columns[4].metric(
        "Medium",
        int(
            summary[
                "medium_findings"
            ]
        ),
    )

    if not findings:
        st.success(
            "No configured data-quality exceptions "
            "were identified."
        )
        return

    findings_frame = pd.DataFrame(
        [
            finding.to_dict()
            for finding in findings
        ]
    )

    default_severities = (
        monitoring_settings.get(
            "severity_filter_default",
            [
                "Critical",
                "High",
                "Medium",
            ],
        )
    )

    severity_filter = st.multiselect(
        "Data-quality severity",
        options=[
            "Critical",
            "High",
            "Medium",
        ],
        default=default_severities,
        key="data_quality_severity_filter",
    )

    filtered = findings_frame[
        findings_frame[
            "severity"
        ].isin(
            severity_filter
        )
    ].copy()

    if filtered.empty:
        st.info(
            "No data-quality findings match "
            "the selected severity filter."
        )
        return

    display_frame = filtered[
        [
            "severity",
            "category",
            "dataset",
            "field_name",
            "finding",
            "affected_records",
            "evidence",
        ]
    ].copy()

    display_frame = display_frame.rename(
        columns={
            "severity": "Severity",
            "category": "Category",
            "dataset": "Dataset",
            "field_name": "Field",
            "finding": "Finding",
            "affected_records": (
                "Affected Records"
            ),
            "evidence": "Evidence",
        }
    )

    st.dataframe(
        display_frame,
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "Data-quality monitoring is deterministic "
        "and read-only. Findings require authorised "
        "review before source-data correction."
    )