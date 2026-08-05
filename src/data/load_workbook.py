"""Metadata-driven Excel workbook ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.column_names import (
    standardise_dataframe_columns,
)


class WorkbookLoadingError(RuntimeError):
    """Raised when workbook ingestion fails."""


@dataclass(frozen=True)
class LoadedDataset:
    """One mapped dataset loaded from Excel."""

    dataset_name: str
    sheet_name: str
    output_table: str
    dataframe: pd.DataFrame
    source_columns: list[str]
    mapped_columns: list[str]


def inspect_available_sheets(
    workbook_path: Path,
) -> list[str]:
    """Return worksheet names available in a workbook."""

    if not workbook_path.is_file():
        raise WorkbookLoadingError(
            f"Workbook not found: {workbook_path}"
        )

    try:
        excel_file = pd.ExcelFile(
            workbook_path,
            engine="openpyxl",
        )
    except Exception as exc:
        raise WorkbookLoadingError(
            f"Unable to open workbook: {workbook_path}"
        ) from exc

    return excel_file.sheet_names


def _apply_column_mapping(
    dataframe: pd.DataFrame,
    column_mappings: dict[str, str],
) -> pd.DataFrame:
    """Map standardised source headings to canonical headings."""

    rename_mapping = {
        source_column: canonical_column
        for source_column, canonical_column
        in column_mappings.items()
        if source_column in dataframe.columns
    }

    return dataframe.rename(
        columns=rename_mapping
    )


def _replace_null_markers(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Convert explicit Excel null markers to missing values."""

    null_markers = {
        "NULL": pd.NA,
        "Null": pd.NA,
        "null": pd.NA,
        "N/A": pd.NA,
        "n/a": pd.NA,
        "NA": pd.NA,
        "": pd.NA,
    }

    return dataframe.replace(
        null_markers
    )


def load_mapped_datasets(
    workbook_path: Path,
    mapping: dict[str, Any],
) -> dict[str, LoadedDataset]:
    """
    Load and map all configured datasets.

    Empty rows are removed, but source values are otherwise preserved.
    """

    available_sheets = inspect_available_sheets(
        workbook_path
    )

    loaded_datasets: dict[str, LoadedDataset] = {}

    for dataset_name, dataset_config in (
        mapping["datasets"].items()
    ):
        sheet_name = dataset_config["sheet_name"]
        required = bool(
            dataset_config.get("required", True)
        )

        if sheet_name not in available_sheets:
            if required:
                raise WorkbookLoadingError(
                    f"Required worksheet is missing: "
                    f"{sheet_name}"
                )

            continue

        try:
            dataframe = pd.read_excel(
                workbook_path,
                sheet_name=sheet_name,
                engine="openpyxl",
            )
        except Exception as exc:
            raise WorkbookLoadingError(
                f"Unable to read worksheet: {sheet_name}"
            ) from exc

        dataframe = dataframe.dropna(
            how="all"
        ).reset_index(drop=True)

        source_columns = [
            str(column)
            for column in dataframe.columns
        ]

        dataframe = standardise_dataframe_columns(
            dataframe
        )

        dataframe = _replace_null_markers(
            dataframe
        )

        dataframe = _apply_column_mapping(
            dataframe,
            dataset_config.get(
                "column_mappings",
                {},
            ),
        )

        loaded_datasets[dataset_name] = (
            LoadedDataset(
                dataset_name=dataset_name,
                sheet_name=sheet_name,
                output_table=dataset_config[
                    "output_table"
                ],
                dataframe=dataframe,
                source_columns=source_columns,
                mapped_columns=list(
                    dataframe.columns
                ),
            )
        )

    if not loaded_datasets:
        raise WorkbookLoadingError(
            "No configured datasets were loaded."
        )

    return loaded_datasets