"""Data-quality checks for ingested aviation datasets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class DataQualityResult:
    """Summary of data-quality findings."""

    dataset_name: str
    row_count: int
    duplicate_rows: int
    completely_empty_rows: int
    missing_values_by_column: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""

        return asdict(self)


def analyse_data_quality(
    dataset_name: str,
    dataframe: pd.DataFrame,
) -> DataQualityResult:
    """Create a basic data-quality profile."""

    missing_values = {
        str(column): int(count)
        for column, count
        in dataframe.isna().sum().items()
    }

    return DataQualityResult(
        dataset_name=dataset_name,
        row_count=len(dataframe),
        duplicate_rows=int(
            dataframe.duplicated().sum()
        ),
        completely_empty_rows=int(
            dataframe.isna().all(axis=1).sum()
        ),
        missing_values_by_column=missing_values,
    )