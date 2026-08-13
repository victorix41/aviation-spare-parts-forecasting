"""Production-readiness and governance-assurance dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboards.dashboard_utils import (
    display_dataframe,
)


def load_production_readiness_summary(
    summary_path: Path,
) -> dict[str, Any] | None:
    """Load the latest production-readiness summary."""

    if not summary_path.exists():
        return None

    try:
        payload = json.loads(
            summary_path.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def readiness_checks_frame(
    summary: dict[str, Any],
) -> pd.DataFrame:
    """Convert readiness checks into a display frame."""

    checks = summary.get(
        "checks",
        [],
    )

    if not isinstance(checks, list):
        return pd.DataFrame()

    records: list[dict[str, Any]] = []

    for check in checks:
        if not isinstance(check, dict):
            continue

        records.append(
            {
                "check_name": check.get(
                    "check_name",
                    "Unknown",
                ),
                "status": check.get(
                    "status",
                    "Unknown",
                ),
                "message": check.get(
                    "message",
                    "",
                ),
            }
        )

    return pd.DataFrame(
        records
    )


def render_production_readiness(
    *,
    project_root: Path,
    reports_directory: Path,
) -> None:
    """Render production-readiness assurance status."""

    st.subheader(
        "Production Readiness & Governance Assurance"
    )

    st.caption(
        "Final technical, assurance and governance "
        "checks for governed management decision support."
    )

    summary_path = (
        reports_directory
        / "production_readiness_summary.json"
    )

    summary = (
        load_production_readiness_summary(
            summary_path
        )
    )

    if summary is None:
        st.warning(
            "No production-readiness summary is "
            "currently available. Run the production-"
            "readiness validation before relying on "
            "this status."
        )
        return

    overall_status = str(
        summary.get(
            "overall_status",
            "Unknown",
        )
    )

    classification = str(
        summary.get(
            "classification",
            "Unavailable",
        )
    )

    human_approval_required = bool(
        summary.get(
            "human_approval_required",
            True,
        )
    )

    automatic_purchasing_enabled = bool(
        summary.get(
            "automatic_purchasing_enabled",
            False,
        )
    )

    inventory_writeback_enabled = bool(
        summary.get(
            "inventory_writeback_enabled",
            False,
        )
    )

    if overall_status == "Passed":
        st.success(
            "Production readiness passed: "
            f"{classification}."
        )
    else:
        st.error(
            "Production readiness has not passed: "
            f"{classification}."
        )

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        "Overall readiness",
        overall_status,
    )

    metric_columns[1].metric(
        "Human approval",
        (
            "Required"
            if human_approval_required
            else "Not required"
        ),
    )

    metric_columns[2].metric(
        "Automatic purchasing",
        (
            "Enabled"
            if automatic_purchasing_enabled
            else "Disabled"
        ),
    )

    metric_columns[3].metric(
        "Inventory write-back",
        (
            "Enabled"
            if inventory_writeback_enabled
            else "Disabled"
        ),
    )

    checks = readiness_checks_frame(
        summary
    )

    if checks.empty:
        st.warning(
            "The production-readiness summary contains "
            "no individual readiness checks."
        )
    else:
        failed_count = int(
            (
                checks["status"]
                != "Passed"
            ).sum()
        )

        st.markdown(
            "**Readiness and assurance checks**"
        )

        if failed_count == 0:
            st.success(
                "All recorded production-readiness "
                "checks passed."
            )
        else:
            st.error(
                f"{failed_count:,} production-readiness "
                "check(s) require attention."
            )

        display_dataframe(
            checks,
            height=420,
        )

    st.info(
        "A Passed readiness result authorises governed "
        "decision support only. It does not authorise "
        "automatic purchasing, inventory write-back, "
        "expenditure approval or operational action. "
        "Human management approval remains required."
    )

    st.caption(
        "Readiness evidence source: "
        f"`{summary_path.relative_to(project_root)}`"
    )