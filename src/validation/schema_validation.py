"""Schema validation for canonical ingestion datasets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class DatasetValidationResult:
    """Validation result for one dataset."""

    dataset_name: str
    row_count: int
    column_count: int
    missing_required_columns: list[str]
    duplicate_column_names: list[str]
    valid: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""

        return asdict(self)


class DatasetSchemaError(ValueError):
    """Raised when a dataset fails schema validation."""


def find_duplicate_columns(
    dataframe: pd.DataFrame,
) -> list[str]:
    """Return duplicate column names."""

    duplicated = dataframe.columns[
        dataframe.columns.duplicated()
    ]

    return sorted(
        set(str(column) for column in duplicated)
    )


def validate_dataset_schema(
    dataset_name: str,
    dataframe: pd.DataFrame,
    required_columns: list[str],
) -> DatasetValidationResult:
    """Validate one dataset against its canonical schema."""

    missing_columns = sorted(
        set(required_columns).difference(
            dataframe.columns
        )
    )

    duplicate_columns = find_duplicate_columns(
        dataframe
    )

    valid = (
        not missing_columns
        and not duplicate_columns
        and not dataframe.empty
    )

    return DatasetValidationResult(
        dataset_name=dataset_name,
        row_count=len(dataframe),
        column_count=len(dataframe.columns),
        missing_required_columns=missing_columns,
        duplicate_column_names=duplicate_columns,
        valid=valid,
    )


def raise_for_invalid_schema(
    result: DatasetValidationResult,
) -> None:
    """Raise a readable error for an invalid result."""

    if result.valid:
        return

    error_parts: list[str] = []

    if result.row_count == 0:
        error_parts.append(
            "dataset contains no records"
        )

    if result.missing_required_columns:
        error_parts.append(
            "missing required columns: "
            + ", ".join(
                result.missing_required_columns
            )
        )

    if result.duplicate_column_names:
        error_parts.append(
            "duplicate columns: "
            + ", ".join(
                result.duplicate_column_names
            )
        )

    raise DatasetSchemaError(
        f"{result.dataset_name} validation failed: "
        + "; ".join(error_parts)
    )