"""Metadata-driven Excel-to-DuckDB ingestion pipeline."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import yaml

from src.data.load_workbook import (
    LoadedDataset,
    load_mapped_datasets,
)
from src.utils.mapping_loader import (
    load_workbook_mapping,
)
from src.validation.data_quality import (
    analyse_data_quality,
)
from src.validation.schema_validation import (
    raise_for_invalid_schema,
    validate_dataset_schema,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_project_settings() -> dict[str, Any]:
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


def save_parquet_dataset(
    dataframe: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write one processed dataset to Parquet."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_parquet(
        output_path,
        index=False,
    )


def write_dataset_to_duckdb(
    connection: duckdb.DuckDBPyConnection,
    loaded_dataset: LoadedDataset,
) -> None:
    """Write one loaded dataset to DuckDB."""

    temporary_view = (
        f"temporary_{loaded_dataset.output_table}"
    )

    connection.register(
        temporary_view,
        loaded_dataset.dataframe,
    )

    try:
        connection.execute(
            f"""
            CREATE OR REPLACE TABLE
            "{loaded_dataset.output_table}"
            AS
            SELECT *
            FROM "{temporary_view}"
            """
        )
    finally:
        connection.unregister(
            temporary_view
        )


def verify_database_row_count(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    expected_count: int,
) -> None:
    """Verify a DuckDB table row count."""

    result = connection.execute(
        f'SELECT COUNT(*) FROM "{table_name}"'
    ).fetchone()

    actual_count = (
        int(result[0])
        if result is not None
        else -1
    )

    if actual_count != expected_count:
        raise RuntimeError(
            f"Row-count mismatch for {table_name}: "
            f"expected {expected_count}, "
            f"found {actual_count}"
        )


def run_ingestion_pipeline() -> dict[str, Any]:
    """Run the complete metadata-driven ingestion."""

    started_at = datetime.now(UTC)

    settings = load_project_settings()
    mapping = load_workbook_mapping()

    raw_directory = (
        PROJECT_ROOT
        / settings["paths"]["raw_data"]
    )

    workbook_path = (
        raw_directory
        / mapping["workbook"]["filename"]
    )

    processed_directory = (
        PROJECT_ROOT
        / settings["paths"]["processed_data"]
    )

    reports_directory = (
        PROJECT_ROOT
        / settings["paths"]["reports"]
    )

    database_path = (
        PROJECT_ROOT
        / settings["paths"]["database"]
    )

    datasets = load_mapped_datasets(
        workbook_path=workbook_path,
        mapping=mapping,
    )

    report_datasets: list[dict[str, Any]] = []

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with duckdb.connect(
        str(database_path)
    ) as connection:
        for dataset_name, loaded_dataset in (
            datasets.items()
        ):
            dataset_config = mapping[
                "datasets"
            ][dataset_name]

            validation_result = (
                validate_dataset_schema(
                    dataset_name=dataset_name,
                    dataframe=(
                        loaded_dataset.dataframe
                    ),
                    required_columns=dataset_config[
                        "required_columns"
                    ],
                )
            )

            raise_for_invalid_schema(
                validation_result
            )

            quality_result = analyse_data_quality(
                dataset_name=dataset_name,
                dataframe=loaded_dataset.dataframe,
            )

            parquet_path = (
                processed_directory
                / f"{loaded_dataset.output_table}.parquet"
            )

            save_parquet_dataset(
                dataframe=loaded_dataset.dataframe,
                output_path=parquet_path,
            )

            write_dataset_to_duckdb(
                connection=connection,
                loaded_dataset=loaded_dataset,
            )

            verify_database_row_count(
                connection=connection,
                table_name=(
                    loaded_dataset.output_table
                ),
                expected_count=len(
                    loaded_dataset.dataframe
                ),
            )

            report_datasets.append(
                {
                    "dataset_name": dataset_name,
                    "sheet_name": (
                        loaded_dataset.sheet_name
                    ),
                    "table_name": (
                        loaded_dataset.output_table
                    ),
                    "row_count": len(
                        loaded_dataset.dataframe
                    ),
                    "column_count": len(
                        loaded_dataset.dataframe.columns
                    ),
                    "mapped_columns": (
                        loaded_dataset.mapped_columns
                    ),
                    "schema_validation": (
                        validation_result.to_dict()
                    ),
                    "data_quality": (
                        quality_result.to_dict()
                    ),
                }
            )

    completed_at = datetime.now(UTC)

    report = {
        "source_workbook": str(workbook_path),
        "database_path": str(database_path),
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "dataset_count": len(report_datasets),
        "total_rows": sum(
            dataset["row_count"]
            for dataset in report_datasets
        ),
        "success": True,
        "datasets": report_datasets,
    }

    reports_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        reports_directory
        / "ingestion_report.json"
    )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
        )

    return report


def print_ingestion_summary(
    report: dict[str, Any],
) -> None:
    """Print a readable ingestion summary."""

    separator = "=" * 72

    print(separator)
    print("AVIATION SPARE PARTS — PHASE 2 INGESTION")
    print(separator)

    for dataset in report["datasets"]:
        print(
            f"✓ {dataset['sheet_name']} "
            f"→ {dataset['table_name']}: "
            f"{dataset['row_count']:,} rows, "
            f"{dataset['column_count']} columns"
        )

    print("-" * 72)
    print(
        f"Datasets loaded: "
        f"{report['dataset_count']}"
    )
    print(
        f"Total records loaded: "
        f"{report['total_rows']:,}"
    )
    print(
        f"Ingestion passed: "
        f"{report['success']}"
    )
    print(separator)


def main() -> None:
    """Command-line entry point."""

    try:
        report = run_ingestion_pipeline()
    except Exception as exc:
        print("=" * 72)
        print("PHASE 2 INGESTION FAILED")
        print("=" * 72)
        print(str(exc))
        raise SystemExit(1) from exc

    print_ingestion_summary(
        report
    )


if __name__ == "__main__":
    main()