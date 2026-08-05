"""Run the aviation spare-parts demand analytics pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import yaml

from src.analytics.demand_engine import (
    run_demand_analysis,
)
from src.analytics.demand_models import (
    DemandAnalyticsSummary,
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
            "Project settings must be a YAML mapping."
        )

    return settings


def load_source_data(
    database_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load inventory and issue history from DuckDB."""

    if not database_path.is_file():
        raise FileNotFoundError(
            "DuckDB database was not found. "
            "Run Phase 2 ingestion first."
        )

    with duckdb.connect(
        str(database_path),
        read_only=True,
    ) as connection:
        inventory = connection.execute(
            """
            SELECT *
            FROM inventory
            """
        ).fetchdf()

        issue_history = connection.execute(
            """
            SELECT *
            FROM issue_history
            """
        ).fetchdf()

    return inventory, issue_history


def write_analysis_tables(
    database_path: Path,
    outputs: dict[str, pd.DataFrame],
) -> None:
    """Write analytics outputs to DuckDB."""

    with duckdb.connect(
        str(database_path)
    ) as connection:
        for table_name, dataframe in (
            outputs.items()
        ):
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


def save_parquet_outputs(
    output_directory: Path,
    outputs: dict[str, pd.DataFrame],
) -> None:
    """Save analytics outputs as Parquet files."""

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for output_name, dataframe in (
        outputs.items()
    ):
        dataframe.to_parquet(
            output_directory
            / f"{output_name}.parquet",
            index=False,
        )


def create_summary(
    demand_metrics: pd.DataFrame,
    monthly_demand: pd.DataFrame,
    *,
    inventory_record_count: int,
    history_start_date: str,
    history_end_date: str,
) -> DemandAnalyticsSummary:
    """Create the Phase 3.1 execution summary."""

    abc_counts = {
        str(key): int(value)
        for key, value in demand_metrics[
            "abc_class"
        ].value_counts().to_dict().items()
    }

    xyz_counts = {
        str(key): int(value)
        for key, value in demand_metrics[
            "xyz_class"
        ].value_counts().to_dict().items()
    }

    pattern_counts = {
        str(key): int(value)
        for key, value in demand_metrics[
            "demand_pattern"
        ].value_counts().to_dict().items()
    }

    active_part_count = int(
        demand_metrics[
            "forecast_eligible"
        ].sum()
    )

    inventory_part_count = int(
        demand_metrics[
            "part_number"
        ].nunique()
    )

    return DemandAnalyticsSummary(
        history_start_date=history_start_date,
        history_end_date=history_end_date,
        history_months=int(
            monthly_demand[
                "demand_month"
            ].nunique()
        ),
        inventory_record_count=inventory_record_count,
        inventory_part_count=inventory_part_count,
        active_demand_part_count=active_part_count,
        no_demand_part_count=(
            inventory_part_count
            - active_part_count
        ),
        monthly_demand_rows=len(
            monthly_demand
        ),
        total_quantity_issued=float(
            demand_metrics[
                "total_quantity_issued"
            ].sum()
        ),
        total_issued_value_usd=float(
            demand_metrics[
                "total_issued_value_usd"
            ].sum()
        ),
        abc_counts=abc_counts,
        xyz_counts=xyz_counts,
        demand_pattern_counts=pattern_counts,
    )


def print_summary(
    summary: DemandAnalyticsSummary,
) -> None:
    """Print a management-readable execution summary."""

    separator = "=" * 72

    print(separator)
    print(
        "AVIATION SPARE PARTS — "
        "PHASE 3.1 DEMAND ANALYTICS"
    )
    print(separator)

    print(
        "History period: "
        f"{summary.history_start_date} "
        f"to {summary.history_end_date}"
    )

    print(
        f"History months: "
        f"{summary.history_months}"
    )

    print(
    f"Inventory records: "
    f"{summary.inventory_record_count:,}"
    )
    
    print(
        f"Unique inventory parts analysed: "
        f"{summary.inventory_part_count:,}"
    )

    print(
        f"Demand-active parts: "
        f"{summary.active_demand_part_count:,}"
    )

    print(
        f"Parts with no demand: "
        f"{summary.no_demand_part_count:,}"
    )

    print(
        f"Monthly demand records: "
        f"{summary.monthly_demand_rows:,}"
    )

    print(
        f"Total quantity issued: "
        f"{summary.total_quantity_issued:,.0f}"
    )

    print(
        "Total issued value: "
        f"USD "
        f"{summary.total_issued_value_usd:,.2f}"
    )

    print()

    print(
        f"ABC classes: "
        f"{summary.abc_counts}"
    )

    print(
        f"XYZ classes: "
        f"{summary.xyz_counts}"
    )

    print(
        "Demand patterns: "
        f"{summary.demand_pattern_counts}"
    )

    print(separator)


def main() -> None:
    """Run Phase 3.1."""

    settings = load_settings()

    database_path = (
        PROJECT_ROOT
        / settings["paths"]["database"]
    )

    processed_directory = (
        PROJECT_ROOT
        / settings["paths"]["processed_data"]
    )

    reports_directory = (
        PROJECT_ROOT
        / settings["paths"]["reports"]
    )

    analytics_settings = settings[
        "analytics"
    ]

    history_start_date = analytics_settings[
        "demand_history"
    ]["start_date"]

    history_end_date = analytics_settings[
        "demand_history"
    ]["end_date"]

    inventory, issue_history = load_source_data(
    database_path
    )

    result = run_demand_analysis(
        inventory=inventory,
        issue_history=issue_history,
        history_start_date=str(
            history_start_date
        ),
        history_end_date=str(
            history_end_date
        ),
        adi_threshold=float(
            analytics_settings[
                "intermittent_demand"
            ]["adi_threshold"]
        ),
        cv_squared_threshold=float(
            analytics_settings[
                "intermittent_demand"
            ]["cv_squared_threshold"]
        ),
        class_x_cv=float(
            analytics_settings[
                "xyz_thresholds"
            ]["class_x_cv"]
        ),
        class_y_cv=float(
            analytics_settings[
                "xyz_thresholds"
            ]["class_y_cv"]
        ),
        class_a_threshold=float(
            analytics_settings[
                "abc_thresholds"
            ][
                "class_a_cumulative_percent"
            ]
        ),
        class_b_threshold=float(
            analytics_settings[
                "abc_thresholds"
            ][
                "class_b_cumulative_percent"
            ]
        ),
    )

    outputs = {
        "monthly_demand": (
            result.monthly_demand
        ),
        "demand_metrics": (
            result.demand_metrics
        ),
        "demand_pareto": (
            result.pareto_analysis
        ),
    }

    save_parquet_outputs(
        processed_directory,
        outputs,
    )

    write_analysis_tables(
        database_path,
        outputs,
    )

    summary = create_summary(
        demand_metrics=(
            result.demand_metrics
        ),
        monthly_demand=(
            result.monthly_demand
        ),
        inventory_record_count=len(inventory),
        history_start_date=str(
            history_start_date
        ),
        history_end_date=str(
            history_end_date
        ),
    )

    reports_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        reports_directory
        / "demand_analytics_summary.json"
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

    print_summary(
        summary
    )


if __name__ == "__main__":
    main()