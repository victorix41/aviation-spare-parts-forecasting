"""Run Phase 3.4 aviation inventory optimisation."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import yaml

from src.optimisation.inventory_engine import (
    run_inventory_optimisation,
)
from src.optimisation.inventory_models import (
    InventoryOptimisationSummary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_settings() -> dict[str, Any]:
    """Load project settings."""

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
            "Settings must be a YAML mapping."
        )

    return settings


def load_source_tables(
    database_path: Path,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Load source tables needed for optimisation."""

    if not database_path.is_file():
        raise FileNotFoundError(
            "DuckDB database was not found."
        )

    with duckdb.connect(
        str(database_path),
        read_only=True,
    ) as connection:
        inventory = connection.execute(
            "SELECT * FROM inventory"
        ).fetchdf()

        demand_metrics = connection.execute(
            "SELECT * FROM demand_metrics"
        ).fetchdf()

        final_forecasts = connection.execute(
            "SELECT * FROM final_part_forecasts"
        ).fetchdf()

    return (
        inventory,
        demand_metrics,
        final_forecasts,
    )


def write_table(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    dataframe: pd.DataFrame,
) -> None:
    """Write one dataframe to DuckDB."""

    temporary_name = (
        f"temporary_{table_name}"
    )

    connection.register(
        temporary_name,
        dataframe,
    )

    try:
        connection.execute(
            f"""
            CREATE OR REPLACE TABLE
            "{table_name}"
            AS
            SELECT *
            FROM "{temporary_name}"
            """
        )
    finally:
        connection.unregister(
            temporary_name
        )


def create_risk_summary(
    optimisation_results: pd.DataFrame,
) -> pd.DataFrame:
    """Create a management-level inventory risk summary."""

    return (
        optimisation_results.groupby(
            "stockout_risk",
            as_index=False,
        )
        .agg(
            part_count=(
                "part_number",
                "nunique",
            ),
            total_current_balance=(
                "current_balance",
                "sum",
            ),
            total_recommended_order_quantity=(
                "recommended_order_quantity",
                "sum",
            ),
            total_inventory_value_usd=(
                "inventory_value_usd",
                "sum",
            ),
            total_procurement_value_usd=(
                "procurement_value_usd",
                "sum",
            ),
        )
        .sort_values(
            "stockout_risk"
        )
        .reset_index(drop=True)
    )


def main() -> None:
    """Run Phase 3.4."""

    settings = load_settings()

    database_path = (
        PROJECT_ROOT
        / settings["paths"]["database"]
    )

    forecast_output_directory = (
        PROJECT_ROOT
        / settings["paths"]["forecasts"]
    )

    reports_directory = (
        PROJECT_ROOT
        / settings["paths"]["reports"]
    )

    optimisation_settings = settings[
        "inventory_optimisation"
    ]

    (
        inventory,
        demand_metrics,
        final_forecasts,
    ) = load_source_tables(
        database_path
    )

    optimisation_results = (
        run_inventory_optimisation(
            inventory=inventory,
            demand_metrics=demand_metrics,
            final_forecasts=final_forecasts,
            settings=optimisation_settings,
        )
    )

    procurement_recommendations = (
        optimisation_results.loc[
            optimisation_results[
                "recommended_order_quantity"
            ]
            > 0
        ]
        .sort_values(
            [
                "procurement_priority",
                "procurement_value_usd",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .reset_index(drop=True)
    )

    risk_summary = create_risk_summary(
        optimisation_results
    )

    output_tables = optimisation_settings[
        "output_tables"
    ]

    table_frames = {
        output_tables[
            "optimisation_results"
        ]: optimisation_results,
        output_tables[
            "procurement_recommendations"
        ]: procurement_recommendations,
        output_tables[
            "risk_summary"
        ]: risk_summary,
    }

    with duckdb.connect(
        str(database_path)
    ) as connection:
        for (
            table_name,
            dataframe,
        ) in table_frames.items():
            write_table(
                connection,
                table_name,
                dataframe,
            )

    forecast_output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for (
        output_name,
        dataframe,
    ) in table_frames.items():
        dataframe.to_parquet(
            forecast_output_directory
            / f"{output_name}.parquet",
            index=False,
        )

    risk_counts = Counter(
        optimisation_results[
            "stockout_risk"
        ].tolist()
    )

    priority_counts = Counter(
        optimisation_results[
            "procurement_priority"
        ].astype(str).tolist()
    )

    summary = InventoryOptimisationSummary(
        inventory_parts=int(
            inventory[
                "part_number"
            ].nunique()
        ),
        forecast_parts=int(
            final_forecasts[
                "part_number"
            ].nunique()
        ),
        optimisation_records=len(
            optimisation_results
        ),
        procurement_recommendations=len(
            procurement_recommendations
        ),
        total_inventory_value_usd=float(
            optimisation_results[
                "inventory_value_usd"
            ].sum()
        ),
        total_recommended_order_quantity=float(
            optimisation_results[
                "recommended_order_quantity"
            ].sum()
        ),
        total_procurement_value_usd=float(
            optimisation_results[
                "procurement_value_usd"
            ].sum()
        ),
        risk_counts={
            str(key): int(value)
            for key, value
            in risk_counts.items()
        },
        priority_counts={
            str(key): int(value)
            for key, value
            in priority_counts.items()
        },
        human_approval_required_count=int(
            optimisation_results[
                "human_approval_required"
            ].sum()
        ),
        success=(
            len(optimisation_results)
            == len(final_forecasts)
        ),
    )

    reports_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        reports_directory
        / "inventory_optimisation_summary.json"
    )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary.to_dict(),
            file,
            indent=2,
        )

    separator = "=" * 72

    print(separator)
    print(
        "AVIATION SPARE PARTS — "
        "PHASE 3.4 INVENTORY OPTIMISATION"
    )
    print(separator)
    print(
        f"Unique inventory parts: "
        f"{summary.inventory_parts:,}"
    )
    print(
        f"Forecast parts optimised: "
        f"{summary.forecast_parts:,}"
    )
    print(
        f"Optimisation records: "
        f"{summary.optimisation_records:,}"
    )
    print(
        f"Procurement recommendations: "
        f"{summary.procurement_recommendations:,}"
    )
    print(
        "Total inventory value: "
        f"USD "
        f"{summary.total_inventory_value_usd:,.2f}"
    )
    print(
        "Recommended order quantity: "
        f"{summary.total_recommended_order_quantity:,.0f}"
    )
    print(
        "Projected procurement value: "
        f"USD "
        f"{summary.total_procurement_value_usd:,.2f}"
    )
    print(
        f"Stockout risks: "
        f"{summary.risk_counts}"
    )
    print(
        "Human approvals required: "
        f"{summary.human_approval_required_count:,}"
    )
    print(
        f"Optimisation passed: "
        f"{summary.success}"
    )
    print(separator)


if __name__ == "__main__":
    main()