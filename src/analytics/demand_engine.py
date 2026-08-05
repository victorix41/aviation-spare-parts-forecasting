"""Demand analytics for aviation spare-parts consumption."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd


class DemandAnalyticsError(ValueError):
    """Raised when demand analytics cannot be completed."""


REQUIRED_INVENTORY_COLUMNS = {
    "part_number",
    "description",
}

REQUIRED_ISSUE_COLUMNS = {
    "part_number",
    "description",
    "issue_date",
    "quantity_issued",
    "unit_price_usd",
    "issued_value_usd",
}


@dataclass(frozen=True)
class DemandAnalysisResult:
    """Container for all demand-analysis outputs."""

    monthly_demand: pd.DataFrame
    demand_metrics: pd.DataFrame
    pareto_analysis: pd.DataFrame


def validate_inventory(
    inventory: pd.DataFrame,
) -> None:
    """Validate the minimum inventory schema."""

    missing_columns = sorted(
        REQUIRED_INVENTORY_COLUMNS.difference(
            inventory.columns
        )
    )

    if missing_columns:
        raise DemandAnalyticsError(
            "Inventory is missing required columns: "
            + ", ".join(missing_columns)
        )

    if inventory.empty:
        raise DemandAnalyticsError(
            "Inventory contains no records."
        )


def validate_issue_history(
    issue_history: pd.DataFrame,
) -> None:
    """Validate the minimum issue-history schema."""

    missing_columns = sorted(
        REQUIRED_ISSUE_COLUMNS.difference(
            issue_history.columns
        )
    )

    if missing_columns:
        raise DemandAnalyticsError(
            "Issue history is missing required columns: "
            + ", ".join(missing_columns)
        )

    if issue_history.empty:
        raise DemandAnalyticsError(
            "Issue history contains no records."
        )


def prepare_inventory(
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare the inventory part master."""

    validate_inventory(inventory)

    output = inventory.copy()

    output = output.loc[
        output["part_number"].notna()
    ].copy()

    output["part_number"] = (
        output["part_number"]
        .astype(str)
        .str.strip()
    )

    output["description"] = (
        output["description"]
        .fillna("Unspecified")
        .astype(str)
        .str.strip()
    )

    output = output.loc[
        output["part_number"].ne("")
    ].copy()

    output = (
        output[
            [
                "part_number",
                "description",
            ]
        ]
        .drop_duplicates(
            subset=["part_number"],
            keep="last",
        )
        .sort_values("part_number")
        .reset_index(drop=True)
    )

    if output.empty:
        raise DemandAnalyticsError(
            "Inventory contains no valid part numbers."
        )

    return output


def prepare_issue_history(
    issue_history: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare issue-history data for demand analysis."""

    validate_issue_history(issue_history)

    output = issue_history.copy()

    output["issue_date"] = pd.to_datetime(
        output["issue_date"],
        errors="coerce",
    )

    output["quantity_issued"] = pd.to_numeric(
        output["quantity_issued"],
        errors="coerce",
    )

    output["unit_price_usd"] = pd.to_numeric(
        output["unit_price_usd"],
        errors="coerce",
    )

    output["issued_value_usd"] = pd.to_numeric(
        output["issued_value_usd"],
        errors="coerce",
    )

    output = output.loc[
        output["issue_date"].notna()
        & output["quantity_issued"].gt(0)
        & output["part_number"].notna()
    ].copy()

    output["part_number"] = (
        output["part_number"]
        .astype(str)
        .str.strip()
    )

    output["description"] = (
        output["description"]
        .fillna("Unspecified")
        .astype(str)
        .str.strip()
    )

    return output.reset_index(drop=True)


def create_monthly_calendar(
    history_start_date: str | date | pd.Timestamp,
    history_end_date: str | date | pd.Timestamp,
) -> pd.DatetimeIndex:
    """Create an inclusive monthly-start calendar."""

    start = pd.Timestamp(history_start_date)
    end = pd.Timestamp(history_end_date)

    if end < start:
        raise DemandAnalyticsError(
            "Demand-history end date cannot precede the start date."
        )

    return pd.date_range(
        start=start.to_period("M").start_time,
        end=end.to_period("M").start_time,
        freq="MS",
    )


def generate_monthly_demand(
    inventory: pd.DataFrame,
    issue_history: pd.DataFrame,
    history_start_date: str | date | pd.Timestamp,
    history_end_date: str | date | pd.Timestamp,
) -> pd.DataFrame:
    """
    Create a complete inventory-part-by-month demand table.

    Every inventory part receives one row for every month, including parts
    with no recorded issues and months with zero demand.
    """

    part_master = prepare_inventory(
        inventory
    )

    prepared_issues = prepare_issue_history(
        issue_history
    )

    start_timestamp = pd.Timestamp(
        history_start_date
    )

    end_timestamp = pd.Timestamp(
        history_end_date
    )

    calendar = create_monthly_calendar(
        history_start_date,
        history_end_date,
    )

    prepared_issues = prepared_issues.loc[
        prepared_issues["issue_date"].between(
            start_timestamp,
            end_timestamp,
            inclusive="both",
        )
    ].copy()

    prepared_issues["demand_month"] = (
        prepared_issues["issue_date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    monthly_actual = (
        prepared_issues.groupby(
            [
                "part_number",
                "demand_month",
            ],
            as_index=False,
        )
        .agg(
            quantity_issued=(
                "quantity_issued",
                "sum",
            ),
            issued_value_usd=(
                "issued_value_usd",
                "sum",
            ),
            issue_transactions=(
                "quantity_issued",
                "size",
            ),
        )
    )

    calendar_frame = pd.DataFrame(
        {
            "demand_month": calendar,
            "_join_key": 1,
        }
    )

    complete_grid = (
        part_master.assign(_join_key=1)
        .merge(
            calendar_frame,
            on="_join_key",
            how="inner",
        )
        .drop(columns="_join_key")
    )

    monthly_demand = complete_grid.merge(
        monthly_actual,
        on=[
            "part_number",
            "demand_month",
        ],
        how="left",
    )

    fill_columns = [
        "quantity_issued",
        "issued_value_usd",
        "issue_transactions",
    ]

    monthly_demand[fill_columns] = (
        monthly_demand[fill_columns]
        .fillna(0)
    )

    monthly_demand["quantity_issued"] = (
        monthly_demand["quantity_issued"]
        .astype(float)
    )

    monthly_demand["issued_value_usd"] = (
        monthly_demand["issued_value_usd"]
        .astype(float)
    )

    monthly_demand["issue_transactions"] = (
        monthly_demand["issue_transactions"]
        .astype(int)
    )

    monthly_demand["demand_occurred"] = (
        monthly_demand["quantity_issued"] > 0
    )

    return monthly_demand.sort_values(
        [
            "part_number",
            "demand_month",
        ]
    ).reset_index(drop=True)


def calculate_average_demand_interval(
    monthly_quantities: pd.Series,
) -> float:
    """Calculate average demand interval."""

    positive_months = int(
        monthly_quantities.gt(0).sum()
    )

    if positive_months == 0:
        return float("inf")

    return float(
        len(monthly_quantities)
        / positive_months
    )


def calculate_cv_squared(
    positive_demand: pd.Series,
) -> float:
    """Calculate squared coefficient of variation for positive demand."""

    values = pd.to_numeric(
        positive_demand,
        errors="coerce",
    ).dropna()

    values = values.loc[
        values > 0
    ]

    if values.empty:
        return float("inf")

    mean_value = float(
        values.mean()
    )

    if mean_value == 0:
        return float("inf")

    standard_deviation = float(
        values.std(ddof=0)
    )

    coefficient_of_variation = (
        standard_deviation / mean_value
    )

    return float(
        coefficient_of_variation**2
    )


def classify_demand_pattern(
    adi: float,
    cv_squared: float,
    *,
    adi_threshold: float,
    cv_squared_threshold: float,
) -> str:
    """Classify demand using ADI and CV²."""

    if not np.isfinite(adi):
        return "No demand"

    if (
        adi <= adi_threshold
        and cv_squared <= cv_squared_threshold
    ):
        return "Smooth"

    if (
        adi <= adi_threshold
        and cv_squared > cv_squared_threshold
    ):
        return "Erratic"

    if (
        adi > adi_threshold
        and cv_squared <= cv_squared_threshold
    ):
        return "Intermittent"

    return "Lumpy"


def classify_xyz(
    coefficient_of_variation: float,
    *,
    class_x_cv: float,
    class_y_cv: float,
) -> str:
    """Classify demand variability into X, Y or Z."""

    if not np.isfinite(
        coefficient_of_variation
    ):
        return "Z"

    if coefficient_of_variation <= class_x_cv:
        return "X"

    if coefficient_of_variation <= class_y_cv:
        return "Y"

    return "Z"


def calculate_abc_classes(
    demand_metrics: pd.DataFrame,
    *,
    class_a_threshold: float,
    class_b_threshold: float,
) -> pd.DataFrame:
    """Assign ABC classes using cumulative issued-value contribution."""

    if not 0 < class_a_threshold < class_b_threshold <= 1:
        raise DemandAnalyticsError(
            "ABC thresholds must satisfy "
            "0 < A threshold < B threshold <= 1."
        )

    output = demand_metrics.sort_values(
        [
            "total_issued_value_usd",
            "part_number",
        ],
        ascending=[
            False,
            True,
        ],
    ).copy()

    total_value = float(
        output["total_issued_value_usd"].sum()
    )

    if total_value <= 0:
        output["issued_value_percent"] = 0.0
        output[
            "cumulative_issued_value_percent"
        ] = 0.0
        output["abc_class"] = "C"
        return output

    output["issued_value_percent"] = (
        output["total_issued_value_usd"]
        / total_value
    )

    output[
        "cumulative_issued_value_percent"
    ] = output[
        "issued_value_percent"
    ].cumsum()

    cumulative_before = (
        output[
            "cumulative_issued_value_percent"
        ]
        - output["issued_value_percent"]
    )

    output["abc_class"] = np.select(
        [
            cumulative_before
            < class_a_threshold,
            cumulative_before
            < class_b_threshold,
        ],
        [
            "A",
            "B",
        ],
        default="C",
    )

    return output


def generate_demand_metrics(
    monthly_demand: pd.DataFrame,
    *,
    adi_threshold: float,
    cv_squared_threshold: float,
    class_x_cv: float,
    class_y_cv: float,
    class_a_threshold: float,
    class_b_threshold: float,
) -> pd.DataFrame:
    """Generate one demand-analytics record per inventory part."""

    metric_rows: list[dict[str, object]] = []

    grouped = monthly_demand.groupby(
        [
            "part_number",
            "description",
        ],
        sort=True,
    )

    for (
        part_number,
        description,
    ), part_data in grouped:
        quantities = (
            part_data["quantity_issued"]
            .astype(float)
        )

        positive_quantities = quantities.loc[
            quantities > 0
        ]

        total_quantity = float(
            quantities.sum()
        )

        average_monthly_demand = float(
            quantities.mean()
        )

        demand_standard_deviation = float(
            quantities.std(ddof=0)
        )

        if average_monthly_demand > 0:
            coefficient_of_variation = (
                demand_standard_deviation
                / average_monthly_demand
            )
        else:
            coefficient_of_variation = (
                float("inf")
            )

        adi = calculate_average_demand_interval(
            quantities
        )

        cv_squared = calculate_cv_squared(
            positive_quantities
        )

        demand_pattern = classify_demand_pattern(
            adi,
            cv_squared,
            adi_threshold=adi_threshold,
            cv_squared_threshold=(
                cv_squared_threshold
            ),
        )

        xyz_class = classify_xyz(
            coefficient_of_variation,
            class_x_cv=class_x_cv,
            class_y_cv=class_y_cv,
        )

        active_demand_months = int(
            quantities.gt(0).sum()
        )

        metric_rows.append(
            {
                "part_number": part_number,
                "description": description,
                "history_months": int(
                    len(quantities)
                ),
                "total_quantity_issued": (
                    total_quantity
                ),
                "total_issued_value_usd": float(
                    part_data[
                        "issued_value_usd"
                    ].sum()
                ),
                "issue_transactions": int(
                    part_data[
                        "issue_transactions"
                    ].sum()
                ),
                "active_demand_months": (
                    active_demand_months
                ),
                "zero_demand_months": int(
                    quantities.eq(0).sum()
                ),
                "average_monthly_demand": (
                    average_monthly_demand
                ),
                "demand_standard_deviation": (
                    demand_standard_deviation
                ),
                "coefficient_of_variation": (
                    coefficient_of_variation
                ),
                "adi": adi,
                "cv_squared": cv_squared,
                "demand_pattern": demand_pattern,
                "xyz_class": xyz_class,
                "forecast_eligible": (
                    active_demand_months > 0
                ),
            }
        )

    metrics = pd.DataFrame(
        metric_rows
    )

    metrics = calculate_abc_classes(
        metrics,
        class_a_threshold=class_a_threshold,
        class_b_threshold=class_b_threshold,
    )

    metrics["abc_xyz_class"] = (
        metrics["abc_class"]
        + metrics["xyz_class"]
    )

    metrics["demand_frequency_percent"] = (
        metrics["active_demand_months"]
        / metrics["history_months"]
    )

    return metrics.reset_index(drop=True)


def generate_pareto_analysis(
    demand_metrics: pd.DataFrame,
) -> pd.DataFrame:
    """Create a part-level Pareto table based on issued value."""

    required_columns = {
        "part_number",
        "description",
        "total_issued_value_usd",
        "issued_value_percent",
        "cumulative_issued_value_percent",
        "abc_class",
    }

    missing = required_columns.difference(
        demand_metrics.columns
    )

    if missing:
        raise DemandAnalyticsError(
            "Demand metrics are missing Pareto columns: "
            + ", ".join(sorted(missing))
        )

    pareto = demand_metrics[
        [
            "part_number",
            "description",
            "total_issued_value_usd",
            "issued_value_percent",
            "cumulative_issued_value_percent",
            "abc_class",
            "demand_pattern",
            "forecast_eligible",
        ]
    ].copy()

    pareto = pareto.sort_values(
        [
            "total_issued_value_usd",
            "part_number",
        ],
        ascending=[
            False,
            True,
        ],
    ).reset_index(drop=True)

    pareto.insert(
        0,
        "pareto_rank",
        range(
            1,
            len(pareto) + 1,
        ),
    )

    return pareto


def run_demand_analysis(
    inventory: pd.DataFrame,
    issue_history: pd.DataFrame,
    *,
    history_start_date: str,
    history_end_date: str,
    adi_threshold: float,
    cv_squared_threshold: float,
    class_x_cv: float,
    class_y_cv: float,
    class_a_threshold: float,
    class_b_threshold: float,
) -> DemandAnalysisResult:
    """Run the complete demand-analysis workflow."""

    monthly_demand = generate_monthly_demand(
        inventory=inventory,
        issue_history=issue_history,
        history_start_date=history_start_date,
        history_end_date=history_end_date,
    )

    demand_metrics = generate_demand_metrics(
        monthly_demand=monthly_demand,
        adi_threshold=adi_threshold,
        cv_squared_threshold=cv_squared_threshold,
        class_x_cv=class_x_cv,
        class_y_cv=class_y_cv,
        class_a_threshold=class_a_threshold,
        class_b_threshold=class_b_threshold,
    )

    pareto_analysis = generate_pareto_analysis(
        demand_metrics
    )

    return DemandAnalysisResult(
        monthly_demand=monthly_demand,
        demand_metrics=demand_metrics,
        pareto_analysis=pareto_analysis,
    )