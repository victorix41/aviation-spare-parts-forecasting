"""Inventory optimisation for aviation spare parts."""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any

import pandas as pd

from src.optimisation.inventory_models import (
    InventoryOptimisationResult,
)


class InventoryOptimisationError(ValueError):
    """Raised when inventory optimisation cannot be completed."""


REQUIRED_INVENTORY_COLUMNS = {
    "part_number",
    "description",
    "unit_price_usd",
    "balance_quantity",
}

REQUIRED_DEMAND_COLUMNS = {
    "part_number",
    "description",
    "average_monthly_demand",
    "demand_standard_deviation",
    "demand_pattern",
}

REQUIRED_FORECAST_COLUMNS = {
    "part_number",
    "description",
    "selected_model",
    "forecast_confidence",
    "forecast_3m",
    "forecast_6m",
    "forecast_12m",
}

REQUIRED_FORECAST_SUMMARY_COLUMNS = {
    "part_number",
    "engineering_criticality",
}


def validate_required_columns(
    dataframe: pd.DataFrame,
    required_columns: set[str],
    dataset_name: str,
) -> None:
    """Validate a required DataFrame schema."""

    missing = sorted(
        required_columns.difference(
            dataframe.columns
        )
    )

    if missing:
        raise InventoryOptimisationError(
            f"{dataset_name} is missing required columns: "
            + ", ".join(missing)
        )

    if dataframe.empty:
        raise InventoryOptimisationError(
            f"{dataset_name} contains no records."
        )


def safe_float(
    value: object,
    default: float = 0.0,
) -> float:
    """Convert a value safely into a finite float."""

    try:
        result = float(value)
    except (TypeError, ValueError):
        return default

    if pd.isna(result) or not math.isfinite(result):
        return default

    return result


def normalise_criticality(
    value: object,
) -> str:
    """Return a standard engineering-criticality value."""

    if value is None or pd.isna(value):
        return "unspecified"

    text = str(value).strip().lower()

    if text in {
        "critical",
        "high",
        "medium",
        "low",
    }:
        return text

    return "unspecified"


def calculate_service_level_z_score(
    service_level: float,
) -> float:
    """Convert a service level into a normal-distribution z-score."""

    if not 0.50 < service_level < 1.0:
        raise InventoryOptimisationError(
            "Service level must be greater than 0.50 "
            "and below 1.00."
        )

    return float(
        NormalDist().inv_cdf(
            service_level
        )
    )


def calculate_lead_time_days(
    purchase_order_date: object,
    delivery_order_date: object,
    *,
    default_lead_time_days: float,
    minimum_lead_time_days: float,
) -> float:
    """Calculate procurement lead time from purchase to delivery."""

    purchase_date = pd.to_datetime(
        purchase_order_date,
        errors="coerce",
    )

    delivery_date = pd.to_datetime(
        delivery_order_date,
        errors="coerce",
    )

    if (
        pd.isna(purchase_date)
        or pd.isna(delivery_date)
    ):
        return float(
            default_lead_time_days
        )

    lead_time = float(
        (
            delivery_date
            - purchase_date
        ).days
    )

    if lead_time < minimum_lead_time_days:
        return float(
            default_lead_time_days
        )

    return lead_time


def calculate_safety_stock(
    *,
    demand_standard_deviation: float,
    lead_time_months: float,
    z_score: float,
) -> float:
    """Calculate safety stock using variability during lead time."""

    if demand_standard_deviation <= 0:
        return 0.0

    return max(
        0.0,
        z_score
        * demand_standard_deviation
        * math.sqrt(
            max(
                lead_time_months,
                0.0,
            )
        ),
    )


def calculate_economic_order_quantity(
    *,
    annual_demand: float,
    ordering_cost_usd: float,
    unit_price_usd: float,
    annual_holding_rate: float,
) -> float:
    """Calculate an economic-order-quantity scenario."""

    if annual_demand <= 0:
        return 0.0

    if ordering_cost_usd <= 0:
        return 0.0

    if unit_price_usd <= 0:
        return 0.0

    if annual_holding_rate <= 0:
        return 0.0

    annual_holding_cost = (
        unit_price_usd
        * annual_holding_rate
    )

    return math.sqrt(
        (
            2
            * annual_demand
            * ordering_cost_usd
        )
        / annual_holding_cost
    )


def calculate_months_of_cover(
    *,
    current_balance: float,
    average_monthly_demand: float,
) -> float | None:
    """Calculate current months of stock cover."""

    if average_monthly_demand <= 0:
        return None

    return max(
        0.0,
        current_balance
        / average_monthly_demand,
    )


def classify_stockout_risk(
    *,
    current_balance: float,
    reorder_point: float,
    months_of_cover: float | None,
    critical_months_cover: float,
    high_months_cover: float,
    medium_months_cover: float,
) -> str:
    """Classify stockout risk."""

    if current_balance <= critical_months_cover:
        return "Critical"

    if current_balance < reorder_point:
        return "High"

    if months_of_cover is None:
        return "Low"

    if months_of_cover < high_months_cover:
        return "High"

    if months_of_cover < medium_months_cover:
        return "Medium"

    return "Low"


def create_recommendation_reason(
    *,
    stockout_risk: str,
    current_balance: float,
    reorder_point: float,
    target_stock: float,
    recommended_order_quantity: float,
    lead_time_days: float,
) -> str:
    """Create an explainable procurement recommendation."""

    if recommended_order_quantity <= 0:
        return (
            "No immediate order is indicated. "
            f"Current balance ({current_balance:.2f}) "
            "meets or exceeds the calculated target stock "
            f"({target_stock:.2f})."
        )

    return (
        f"{stockout_risk} stock risk. "
        f"Current balance ({current_balance:.2f}) is below "
        "the calculated inventory requirement. "
        f"Reorder point: {reorder_point:.2f}; "
        f"target stock: {target_stock:.2f}; "
        f"average lead time: {lead_time_days:.1f} days. "
        f"Recommended order quantity: "
        f"{recommended_order_quantity:.0f} units, "
        "subject to authorised human review."
    )


def prepare_inventory_summary(
    inventory: pd.DataFrame,
    *,
    default_lead_time_days: float,
    minimum_lead_time_days: float,
) -> pd.DataFrame:
    """Aggregate inventory lots into one record per part number."""

    validate_required_columns(
        inventory,
        REQUIRED_INVENTORY_COLUMNS,
        "inventory",
    )

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

    output["balance_quantity"] = (
        pd.to_numeric(
            output["balance_quantity"],
            errors="coerce",
        )
        .fillna(0.0)
    )

    output["unit_price_usd"] = (
        pd.to_numeric(
            output["unit_price_usd"],
            errors="coerce",
        )
        .fillna(0.0)
    )

    if (
        "purchase_order_date"
        not in output.columns
    ):
        output[
            "purchase_order_date"
        ] = pd.NaT

    if (
        "delivery_order_date"
        not in output.columns
    ):
        output[
            "delivery_order_date"
        ] = pd.NaT

    output["lead_time_days"] = output.apply(
        lambda row: calculate_lead_time_days(
            row["purchase_order_date"],
            row["delivery_order_date"],
            default_lead_time_days=(
                default_lead_time_days
            ),
            minimum_lead_time_days=(
                minimum_lead_time_days
            ),
        ),
        axis=1,
    )

    output[
        "inventory_line_value_usd"
    ] = (
        output["balance_quantity"]
        * output["unit_price_usd"]
    )

    aggregated = (
        output.groupby(
            "part_number",
            as_index=False,
        )
        .agg(
            description=(
                "description",
                "last",
            ),
            inventory_record_count=(
                "part_number",
                "size",
            ),
            current_balance=(
                "balance_quantity",
                "sum",
            ),
            unit_price_usd=(
                "unit_price_usd",
                "max",
            ),
            inventory_value_usd=(
                "inventory_line_value_usd",
                "sum",
            ),
            average_lead_time_days=(
                "lead_time_days",
                "mean",
            ),
        )
    )

    return aggregated


def prepare_criticality_lookup(
    forecast_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare one engineering-criticality record per part."""

    validate_required_columns(
        forecast_summary,
        REQUIRED_FORECAST_SUMMARY_COLUMNS,
        "forecast_summary",
    )

    criticality_lookup = (
        forecast_summary[
            [
                "part_number",
                "engineering_criticality",
            ]
        ]
        .copy()
    )

    criticality_lookup = (
        criticality_lookup.loc[
            criticality_lookup[
                "part_number"
            ].notna()
        ]
        .copy()
    )

    criticality_lookup["part_number"] = (
        criticality_lookup[
            "part_number"
        ]
        .astype(str)
        .str.strip()
    )

    criticality_lookup[
        "engineering_criticality"
    ] = (
        criticality_lookup[
            "engineering_criticality"
        ]
        .fillna("Unspecified")
        .astype(str)
        .str.strip()
    )

    criticality_lookup = (
        criticality_lookup
        .drop_duplicates(
            subset=["part_number"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    return criticality_lookup


def run_inventory_optimisation(
    *,
    inventory: pd.DataFrame,
    demand_metrics: pd.DataFrame,
    final_forecasts: pd.DataFrame,
    forecast_summary: pd.DataFrame,
    settings: dict[str, Any],
) -> pd.DataFrame:
    """Run inventory optimisation for forecast-eligible parts."""

    validate_required_columns(
        demand_metrics,
        REQUIRED_DEMAND_COLUMNS,
        "demand_metrics",
    )

    validate_required_columns(
        final_forecasts,
        REQUIRED_FORECAST_COLUMNS,
        "final_forecasts",
    )

    validate_required_columns(
        forecast_summary,
        REQUIRED_FORECAST_SUMMARY_COLUMNS,
        "forecast_summary",
    )

    days_per_month = float(
        settings["days_per_month"]
    )

    default_lead_time_days = float(
        settings[
            "default_lead_time_days"
        ]
    )

    minimum_lead_time_days = float(
        settings[
            "minimum_lead_time_days"
        ]
    )

    inventory_summary = (
        prepare_inventory_summary(
            inventory,
            default_lead_time_days=(
                default_lead_time_days
            ),
            minimum_lead_time_days=(
                minimum_lead_time_days
            ),
        )
    )

    criticality_lookup = (
        prepare_criticality_lookup(
            forecast_summary
        )
    )

    merged = (
        final_forecasts.merge(
            demand_metrics[
                [
                    "part_number",
                    "average_monthly_demand",
                    "demand_standard_deviation",
                ]
            ],
            on="part_number",
            how="left",
        )
        .merge(
            inventory_summary,
            on="part_number",
            how="left",
            suffixes=(
                "_forecast",
                "_inventory",
            ),
        )
        .merge(
            criticality_lookup,
            on="part_number",
            how="left",
        )
    )

    result_rows: list[
        dict[str, Any]
    ] = []

    service_levels = settings[
        "service_levels"
    ]

    eoq_settings = settings["eoq"]

    risk_settings = settings[
        "risk_thresholds"
    ]

    priority_settings = settings[
        "procurement_priority"
    ]

    governance_settings = settings[
        "governance"
    ]

    include_safety_stock = bool(
        settings["target_stock"][
            "include_safety_stock"
        ]
    )

    for row in merged.itertuples(
        index=False
    ):
        current_balance = safe_float(
            getattr(
                row,
                "current_balance",
                0.0,
            )
        )

        unit_price_usd = safe_float(
            getattr(
                row,
                "unit_price_usd",
                0.0,
            )
        )

        average_monthly_demand = (
            safe_float(
                getattr(
                    row,
                    "average_monthly_demand",
                    0.0,
                )
            )
        )

        demand_standard_deviation = (
            safe_float(
                getattr(
                    row,
                    "demand_standard_deviation",
                    0.0,
                )
            )
        )

        lead_time_days = safe_float(
            getattr(
                row,
                "average_lead_time_days",
                default_lead_time_days,
            ),
            default=default_lead_time_days,
        )

        if lead_time_days <= 0:
            lead_time_days = (
                default_lead_time_days
            )

        lead_time_months = (
            lead_time_days
            / days_per_month
        )

        criticality = normalise_criticality(
            getattr(
                row,
                "engineering_criticality",
                "unspecified",
            )
        )

        service_level = float(
            service_levels.get(
                criticality,
                service_levels[
                    "unspecified"
                ],
            )
        )

        z_score = (
            calculate_service_level_z_score(
                service_level
            )
        )

        safety_stock = (
            calculate_safety_stock(
                demand_standard_deviation=(
                    demand_standard_deviation
                ),
                lead_time_months=(
                    lead_time_months
                ),
                z_score=z_score,
            )
        )

        demand_during_lead_time = (
            average_monthly_demand
            * lead_time_months
        )

        reorder_point = (
            demand_during_lead_time
            + safety_stock
        )

        forecast_3m = safe_float(
            getattr(
                row,
                "forecast_3m",
                0.0,
            )
        )

        forecast_6m = safe_float(
            getattr(
                row,
                "forecast_6m",
                0.0,
            )
        )

        forecast_12m = safe_float(
            getattr(
                row,
                "forecast_12m",
                0.0,
            )
        )

        if bool(
            eoq_settings["enabled"]
        ):
            economic_order_quantity = (
                calculate_economic_order_quantity(
                    annual_demand=forecast_12m,
                    ordering_cost_usd=float(
                        eoq_settings[
                            "ordering_cost_usd"
                        ]
                    ),
                    unit_price_usd=(
                        unit_price_usd
                    ),
                    annual_holding_rate=float(
                        eoq_settings[
                            "annual_holding_rate"
                        ]
                    ),
                )
            )
        else:
            economic_order_quantity = 0.0

        target_stock = forecast_12m

        if include_safety_stock:
            target_stock += safety_stock

        recommended_order_quantity = max(
            0.0,
            float(
                math.ceil(
                    target_stock
                    - current_balance
                )
            ),
        )

        months_of_cover = (
            calculate_months_of_cover(
                current_balance=current_balance,
                average_monthly_demand=(
                    average_monthly_demand
                ),
            )
        )

        stockout_risk = (
            classify_stockout_risk(
                current_balance=current_balance,
                reorder_point=reorder_point,
                months_of_cover=(
                    months_of_cover
                ),
                critical_months_cover=float(
                    risk_settings[
                        "critical_months_cover"
                    ]
                ),
                high_months_cover=float(
                    risk_settings[
                        "high_months_cover"
                    ]
                ),
                medium_months_cover=float(
                    risk_settings[
                        "medium_months_cover"
                    ]
                ),
            )
        )

        priority = int(
            priority_settings[
                stockout_risk.lower()
            ]
        )

        procurement_value = (
            recommended_order_quantity
            * unit_price_usd
        )

        recommendation_reason = (
            create_recommendation_reason(
                stockout_risk=stockout_risk,
                current_balance=current_balance,
                reorder_point=reorder_point,
                target_stock=target_stock,
                recommended_order_quantity=(
                    recommended_order_quantity
                ),
                lead_time_days=(
                    lead_time_days
                ),
            )
        )

        description = getattr(
            row,
            "description_forecast",
            None,
        )

        if (
            description is None
            or pd.isna(description)
            or not str(description).strip()
        ):
            description = getattr(
                row,
                "description_inventory",
                "Unspecified",
            )

        result = InventoryOptimisationResult(
            part_number=str(
                row.part_number
            ),
            description=str(
                description
            ),
            engineering_criticality=(
                criticality.title()
            ),
            demand_pattern=str(
                row.demand_pattern
            ),
            selected_forecast_model=str(
                row.selected_model
            ),
            forecast_confidence=str(
                row.forecast_confidence
            ),
            inventory_record_count=int(
                safe_float(
                    getattr(
                        row,
                        "inventory_record_count",
                        0,
                    )
                )
            ),
            current_balance=current_balance,
            unit_price_usd=unit_price_usd,
            inventory_value_usd=(
                safe_float(
                    getattr(
                        row,
                        "inventory_value_usd",
                        0.0,
                    )
                )
            ),
            average_monthly_demand=(
                average_monthly_demand
            ),
            demand_standard_deviation=(
                demand_standard_deviation
            ),
            forecast_3m=forecast_3m,
            forecast_6m=forecast_6m,
            forecast_12m=forecast_12m,
            average_lead_time_days=(
                lead_time_days
            ),
            lead_time_months=(
                lead_time_months
            ),
            demand_during_lead_time=(
                demand_during_lead_time
            ),
            service_level=service_level,
            service_level_z_score=(
                z_score
            ),
            safety_stock=safety_stock,
            reorder_point=reorder_point,
            economic_order_quantity=(
                economic_order_quantity
            ),
            target_stock=target_stock,
            recommended_order_quantity=(
                recommended_order_quantity
            ),
            months_of_stock_cover=(
                months_of_cover
            ),
            estimated_stockout_months=(
                months_of_cover
            ),
            stockout_risk=stockout_risk,
            procurement_priority=priority,
            procurement_value_usd=(
                procurement_value
            ),
            automatic_purchase_order_allowed=bool(
                governance_settings[
                    "automatic_purchase_orders"
                ]
            ),
            human_approval_required=bool(
                governance_settings[
                    "human_approval_required"
                ]
            ),
            recommendation_status=(
                "Order review required"
                if recommended_order_quantity > 0
                else "Monitor"
            ),
            recommendation_reason=(
                recommendation_reason
            ),
        )

        result_rows.append(
            result.to_dict()
        )

    return pd.DataFrame(
        result_rows
    )