"""Management alert and exception dashboard component."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analytics.management_alerts import (
    build_assurance_alerts,
    build_inventory_alerts,
    sort_alerts,
)
from src.dashboards.data_access import (
    DashboardRepository,
)


def render_management_alerts(
    *,
    repository: DashboardRepository,
    settings: dict,
    target_role: str | None = None,
) -> None:
    """Render consolidated management alerts."""

    alert_settings = (
        settings
        .get(
            "management_alerts",
            {},
        )
    )

    if not bool(
        alert_settings.get(
            "enabled",
            True,
        )
    ):
        return

    thresholds = (
        alert_settings
        .get(
            "thresholds",
            {},
        )
    )

    finance_settings = (
        thresholds.get(
            "finance",
            {},
        )
    )

    operations_settings = (
        thresholds.get(
            "operations",
            {},
        )
    )

    engineering_settings = (
        thresholds.get(
            "engineering",
            {},
        )
    )

    quality_settings = (
        thresholds.get(
            "quality",
            {},
        )
    )

    st.markdown(
        "### Management Alerts and Exceptions"
    )

    inventory = (
        repository
        .load_management_alert_inventory()
    )

    assurance = (
        repository
        .load_management_alert_assurance()
    )

    inventory_alerts = (
        build_inventory_alerts(
            inventory,
            finance_high_value_usd=float(
                finance_settings.get(
                    "high_single_part_value_usd",
                    100000,
                )
            ),
            operations_critical_risks=set(
                operations_settings.get(
                    "critical_stockout_risk",
                    [
                        "Critical",
                    ],
                )
            ),
            engineering_high_risks=set(
                engineering_settings.get(
                    "high_risk_levels",
                    [
                        "Critical",
                        "High",
                    ],
                )
            ),
            engineering_low_confidence=set(
                engineering_settings.get(
                    "low_forecast_confidence",
                    [
                        "Low",
                    ],
                )
            ),
        )
    )

    assurance_alerts = (
        build_assurance_alerts(
            assurance,
            require_passed=bool(
                quality_settings.get(
                    "require_assurance_passed",
                    True,
                )
            ),
            require_evidence_complete=bool(
                quality_settings.get(
                    "require_evidence_complete",
                    True,
                )
            ),
            require_governance_compliant=bool(
                quality_settings.get(
                    "require_governance_compliant",
                    True,
                )
            ),
            require_display_approval=bool(
                quality_settings.get(
                    "require_management_display_approval",
                    True,
                )
            ),
        )
    )

    alerts = sort_alerts(
        inventory_alerts
        + assurance_alerts
    )

    if target_role is not None:
        alerts = [
            alert
            for alert in alerts
            if alert.target_role
            == target_role
        ]

    if not alerts:
        st.success(
            "No active management exceptions "
            "were identified for this view."
        )
        return

    alert_frame = pd.DataFrame(
        [
            alert.to_dict()
            for alert in alerts
        ]
    )

    critical_count = int(
        (
            alert_frame["severity"]
            == "Critical"
        ).sum()
    )

    high_count = int(
        (
            alert_frame["severity"]
            == "High"
        ).sum()
    )

    total_count = len(
        alert_frame
    )

    affected_parts = int(
        alert_frame[
            "part_number"
        ]
        .dropna()
        .nunique()
    )

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        "Active alerts",
        total_count,
    )

    metric_columns[1].metric(
        "Critical",
        critical_count,
    )

    metric_columns[2].metric(
        "High",
        high_count,
    )

    metric_columns[3].metric(
        "Affected parts",
        affected_parts,
    )

    default_severities = (
        alert_settings.get(
            "severity_filter_default",
            [
                "Critical",
                "High",
            ],
        )
    )

    severity_filter = st.multiselect(
        "Alert severity",
        options=[
            "Critical",
            "High",
            "Medium",
            "Info",
        ],
        default=default_severities,
        key=(
            "management_alert_severity_"
            + str(
                target_role
                or "all"
            )
        ),
    )

    filtered = alert_frame[
        alert_frame[
            "severity"
        ].isin(
            severity_filter
        )
    ].copy()

    if filtered.empty:
        st.info(
            "No alerts match the selected "
            "severity filter."
        )
        return

    display_columns = [
        "severity",
        "alert_type",
        "target_role",
        "part_number",
        "title",
        "message",
        "evidence",
    ]

    display_frame = filtered[
        display_columns
    ].copy()

    display_frame = display_frame.rename(
        columns={
            "severity": "Severity",
            "alert_type": "Alert Type",
            "target_role": "Target Role",
            "part_number": "Part Number",
            "title": "Alert",
            "message": "Management Action",
            "evidence": "Supporting Evidence",
        }
    )

    st.dataframe(
        display_frame,
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "Alerts are deterministic decision-support "
        "exceptions derived from validated analytical "
        "outputs. Human review remains mandatory."
    )