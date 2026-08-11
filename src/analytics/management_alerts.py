"""Deterministic management-alert generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ManagementAlert:
    """One deterministic management alert."""

    alert_type: str
    severity: str
    target_role: str
    title: str
    message: str
    part_number: str | None
    source_table: str
    evidence: str
    human_review_required: bool = True

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """Return a serialisable alert."""

        return asdict(self)


def _safe_float(
    value: Any,
) -> float | None:
    """Safely convert a value to float."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (
        TypeError,
        ValueError,
    ):
        pass

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def build_inventory_alerts(
    optimisation: pd.DataFrame,
    *,
    finance_high_value_usd: float = 100000.0,
    operations_critical_risks: set[str] | None = None,
    engineering_high_risks: set[str] | None = None,
    engineering_low_confidence: set[str] | None = None,
) -> list[ManagementAlert]:
    """Build stock and procurement alerts."""

    alerts: list[ManagementAlert] = []

    if operations_critical_risks is None:
        operations_critical_risks = {
            "Critical",
        }

    if engineering_high_risks is None:
        engineering_high_risks = {
            "Critical",
            "High",
        }

    if engineering_low_confidence is None:
        engineering_low_confidence = {
            "Low",
        }

    if optimisation.empty:
        return alerts

    for row in optimisation.itertuples(
        index=False
    ):
        part_number = str(
            getattr(
                row,
                "part_number",
                "",
            )
            or ""
        )

        stockout_risk = str(
            getattr(
                row,
                "stockout_risk",
                "",
            )
            or ""
        )

        confidence = str(
            getattr(
                row,
                "forecast_confidence",
                "",
            )
            or ""
        )

        procurement_value = (
            _safe_float(
                getattr(
                    row,
                    "procurement_value_usd",
                    None,
                )
            )
            or 0.0
        )

        recommended_quantity = (
            _safe_float(
                getattr(
                    row,
                    "recommended_order_quantity",
                    None,
                )
            )
            or 0.0
        )

        current_balance = (
            _safe_float(
                getattr(
                    row,
                    "current_balance",
                    None,
                )
            )
            or 0.0
        )

        if stockout_risk in operations_critical_risks:
            alerts.append(
                ManagementAlert(
                    alert_type="Stockout Risk",
                    severity="Critical",
                    target_role=(
                        "Operations Manager"
                    ),
                    title=(
                        f"Critical stockout risk: "
                        f"{part_number}"
                    ),
                    message=(
                        "Immediate operational review "
                        "is required."
                    ),
                    part_number=part_number,
                    source_table=(
                        "inventory_optimisation_results"
                    ),
                    evidence=(
                        f"Stockout risk={stockout_risk}; "
                        f"current balance="
                        f"{current_balance:,.2f}; "
                        f"recommended quantity="
                        f"{recommended_quantity:,.0f}."
                    ),
                )
            )

        if (
            stockout_risk
            in engineering_high_risks
            and confidence
            in engineering_low_confidence
        ):
            alerts.append(
                ManagementAlert(
                    alert_type=(
                        "Forecast Uncertainty"
                    ),
                    severity="High",
                    target_role=(
                        "Engineering Manager"
                    ),
                    title=(
                        "Low-confidence forecast for "
                        f"high-risk part: {part_number}"
                    ),
                    message=(
                        "Review forecast assumptions "
                        "before procurement commitment."
                    ),
                    part_number=part_number,
                    source_table=(
                        "inventory_optimisation_results"
                    ),
                    evidence=(
                        f"Stockout risk={stockout_risk}; "
                        f"forecast confidence="
                        f"{confidence}."
                    ),
                )
            )

        if (
            procurement_value
            >= finance_high_value_usd
        ):
            alerts.append(
                ManagementAlert(
                    alert_type=(
                        "High Procurement Exposure"
                    ),
                    severity="High",
                    target_role=(
                        "Finance Manager"
                    ),
                    title=(
                        "High-value procurement review: "
                        f"{part_number}"
                    ),
                    message=(
                        "Individual financial and "
                        "commercial review is required."
                    ),
                    part_number=part_number,
                    source_table=(
                        "inventory_optimisation_results"
                    ),
                    evidence=(
                        "Projected procurement value="
                        f"USD "
                        f"{procurement_value:,.2f}."
                    ),
                )
            )

    return alerts


def build_assurance_alerts(
    findings: pd.DataFrame,
    *,
    require_passed: bool = True,
    require_evidence_complete: bool = True,
    require_governance_compliant: bool = True,
    require_display_approval: bool = True,
) -> list[ManagementAlert]:
    """Build alerts for failed assurance controls."""

    alerts: list[ManagementAlert] = []

    if findings.empty:
        return alerts

    for row in findings.itertuples(
        index=False
    ):
        assurance_status = str(
            getattr(
                row,
                "assurance_status",
                "",
            )
            or ""
        )

        evidence_complete = bool(
            getattr(
                row,
                "evidence_complete",
                False,
            )
        )

        governance_compliant = bool(
            getattr(
                row,
                "governance_compliant",
                False,
            )
        )

        display_approved = bool(
            getattr(
                row,
                "approved_for_management_display",
                False,
            )
        )

        recommendation_id = str(
            getattr(
                row,
                "recommendation_id",
                "",
            )
            or ""
        )

        assurance_exception = False

        if (
            require_passed
            and assurance_status != "Passed"
        ):
            assurance_exception = True

        if (
            require_evidence_complete
            and not evidence_complete
        ):
            assurance_exception = True

        if (
            require_governance_compliant
            and not governance_compliant
        ):
            assurance_exception = True

        if (
            require_display_approval
            and not display_approved
        ):
            assurance_exception = True

        if assurance_exception:
            alerts.append(
                ManagementAlert(
                    alert_type="Assurance Exception",
                    severity="Critical",
                    target_role="Quality Manager",
                    title=(
                        "Agent assurance exception: "
                        f"{recommendation_id}"
                    ),
                    message=(
                        "The recommendation must not "
                        "be relied upon until the "
                        "assurance exception is resolved."
                    ),
                    part_number=None,
                    source_table=(
                        "agent_assurance_findings"
                    ),
                    evidence=(
                        f"Assurance={assurance_status}; "
                        f"evidence complete="
                        f"{evidence_complete}; "
                        f"governance compliant="
                        f"{governance_compliant}; "
                        f"display approved="
                        f"{display_approved}."
                    ),
                )
            )

    return alerts


def sort_alerts(
    alerts: list[ManagementAlert],
) -> list[ManagementAlert]:
    """Sort alerts by management severity."""

    severity_order = {
        "Critical": 1,
        "High": 2,
        "Medium": 3,
        "Info": 4,
    }

    return sorted(
        alerts,
        key=lambda alert: (
            severity_order.get(
                alert.severity,
                99,
            ),
            alert.target_role,
            alert.title,
        ),
    )