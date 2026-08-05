"""Utilities for standardising spreadsheet column names."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


def standardise_column_name(column_name: object) -> str:
    """
    Convert a spreadsheet heading into lowercase snake_case.

    Examples
    --------
    "Part Number" -> "part_number"
    "Unit Price (USD)" -> "unit_price_usd"
    "12M Forecast" -> "12m_forecast"
    """

    value = "" if column_name is None else str(column_name).strip()

    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()

    value = value.replace("&", " and ")
    value = value.replace("%", " percent ")

    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)

    return value.strip("_") or "unnamed"


def make_unique_column_names(
    column_names: list[object],
) -> list[str]:
    """Standardise headings and make duplicate names unique."""

    counts: dict[str, int] = {}
    output: list[str] = []

    for column_name in column_names:
        base_name = standardise_column_name(column_name)
        counts[base_name] = counts.get(base_name, 0) + 1

        if counts[base_name] == 1:
            output.append(base_name)
        else:
            output.append(
                f"{base_name}_{counts[base_name]}"
            )

    return output


def standardise_dataframe_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Return a copy with standardised, unique column names."""

    output = dataframe.copy()

    output.columns = make_unique_column_names(
        list(output.columns)
    )

    return output