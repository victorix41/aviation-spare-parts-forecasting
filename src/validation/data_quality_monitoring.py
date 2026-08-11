"""Deterministic data-quality monitoring for management use."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class DataQualityFinding:
    """One deterministic data-quality finding."""

    category: str
    severity: str
    dataset: str
    field_name: str | None
    finding: str
    affected_records: int
    evidence: str

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """Return a serialisable finding."""

        return asdict(self)


def _missing_count(
    dataframe: pd.DataFrame,
    column_name: str,
) -> int:
    """Count null and blank values in a column."""

    if column_name not in dataframe.columns:
        return 0

    series = dataframe[
        column_name
    ]

    missing = series.isna()

    if (
        pd.api.types
        .is_object_dtype(
            series
        )
        or pd.api.types
        .is_string_dtype(
            series
        )
    ):
        blank = (
            series
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
        )

        missing = (
            missing
            | blank
        )

    return int(
        missing.sum()
    )


def check_required_columns(
    *,
    dataframe: pd.DataFrame,
    dataset: str,
    required_columns: list[str],
) -> list[DataQualityFinding]:
    """Check whether required columns exist."""

    findings: list[DataQualityFinding] = []

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    for column in missing_columns:
        findings.append(
            DataQualityFinding(
                category="Schema",
                severity="Critical",
                dataset=dataset,
                field_name=column,
                finding=(
                    "Required column is missing."
                ),
                affected_records=len(
                    dataframe
                ),
                evidence=(
                    f"Required field '{column}' "
                    f"was not found in {dataset}."
                ),
            )
        )

    return findings


def check_required_values(
    *,
    dataframe: pd.DataFrame,
    dataset: str,
    required_columns: list[str],
) -> list[DataQualityFinding]:
    """Check missing values in required fields."""

    findings: list[DataQualityFinding] = []

    for column in required_columns:
        if column not in dataframe.columns:
            continue

        missing = _missing_count(
            dataframe,
            column,
        )

        if missing > 0:
            findings.append(
                DataQualityFinding(
                    category="Completeness",
                    severity="High",
                    dataset=dataset,
                    field_name=column,
                    finding=(
                        "Required values are missing."
                    ),
                    affected_records=missing,
                    evidence=(
                        f"{missing:,} records in "
                        f"{dataset} have no value "
                        f"for '{column}'."
                    ),
                )
            )

    return findings


def check_duplicate_keys(
    *,
    dataframe: pd.DataFrame,
    dataset: str,
    key_columns: list[str],
) -> list[DataQualityFinding]:
    """Check duplicate business keys."""

    if any(
        column not in dataframe.columns
        for column in key_columns
    ):
        return []

    duplicated = dataframe.duplicated(
        subset=key_columns,
        keep=False,
    )

    duplicate_count = int(
        duplicated.sum()
    )

    if duplicate_count == 0:
        return []

    return [
        DataQualityFinding(
            category="Uniqueness",
            severity="High",
            dataset=dataset,
            field_name=", ".join(
                key_columns
            ),
            finding=(
                "Duplicate business-key records detected."
            ),
            affected_records=duplicate_count,
            evidence=(
                f"{duplicate_count:,} records in "
                f"{dataset} share duplicate key values."
            ),
        )
    ]


def check_negative_values(
    *,
    dataframe: pd.DataFrame,
    dataset: str,
    numeric_columns: list[str],
) -> list[DataQualityFinding]:
    """Check for invalid negative numeric values."""

    findings: list[DataQualityFinding] = []

    for column in numeric_columns:
        if column not in dataframe.columns:
            continue

        values = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

        invalid_count = int(
            (values < 0).sum()
        )

        if invalid_count > 0:
            findings.append(
                DataQualityFinding(
                    category="Validity",
                    severity="High",
                    dataset=dataset,
                    field_name=column,
                    finding=(
                        "Negative values detected."
                    ),
                    affected_records=invalid_count,
                    evidence=(
                        f"{invalid_count:,} records in "
                        f"{dataset} contain negative "
                        f"values in '{column}'."
                    ),
                )
            )

    return findings


def check_future_dates(
    *,
    dataframe: pd.DataFrame,
    dataset: str,
    date_columns: list[str],
    as_of_date: datetime | None = None,
) -> list[DataQualityFinding]:
    """Check unexpected future dates."""

    findings: list[DataQualityFinding] = []

    if as_of_date is None:
        as_of_date = datetime.now(
            timezone.utc
        )

    for column in date_columns:
        if column not in dataframe.columns:
            continue

        dates = pd.to_datetime(
            dataframe[column],
            errors="coerce",
            utc=True,
        )

        future_count = int(
            (
                dates
                > pd.Timestamp(
                    as_of_date
                )
            ).sum()
        )

        if future_count > 0:
            findings.append(
                DataQualityFinding(
                    category="Validity",
                    severity="Medium",
                    dataset=dataset,
                    field_name=column,
                    finding=(
                        "Future-dated records detected."
                    ),
                    affected_records=future_count,
                    evidence=(
                        f"{future_count:,} records in "
                        f"{dataset} contain a future "
                        f"date in '{column}'."
                    ),
                )
            )

    return findings


def summarise_data_quality(
    findings: list[DataQualityFinding],
) -> dict[str, int | str]:
    """Summarise data-quality findings."""

    critical = sum(
        finding.severity == "Critical"
        for finding in findings
    )

    high = sum(
        finding.severity == "High"
        for finding in findings
    )

    medium = sum(
        finding.severity == "Medium"
        for finding in findings
    )

    total = len(
        findings
    )

    if critical > 0:
        status = "Critical"
    elif high > 0:
        status = "Attention Required"
    elif medium > 0:
        status = "Monitor"
    else:
        status = "Passed"

    return {
        "status": status,
        "total_findings": total,
        "critical_findings": critical,
        "high_findings": high,
        "medium_findings": medium,
    }

def check_data_staleness(
    *,
    dataframe: pd.DataFrame,
    dataset: str,
    date_column: str,
    reference_date: datetime,
    stale_after_days: int,
) -> list[DataQualityFinding]:
    """Check whether the latest available record is stale."""

    if date_column not in dataframe.columns:
        return []

    dates = pd.to_datetime(
        dataframe[
            date_column
        ],
        errors="coerce",
        utc=True,
    )

    valid_dates = dates.dropna()

    if valid_dates.empty:
        return [
            DataQualityFinding(
                category="Freshness",
                severity="High",
                dataset=dataset,
                field_name=date_column,
                finding=(
                    "No valid dates are available "
                    "for freshness monitoring."
                ),
                affected_records=len(
                    dataframe
                ),
                evidence=(
                    f"No valid '{date_column}' values "
                    f"were found in {dataset}."
                ),
            )
        ]

    latest_date = valid_dates.max()

    reference_timestamp = pd.Timestamp(
        reference_date
    )

    if reference_timestamp.tzinfo is None:
        reference_timestamp = (
            reference_timestamp.tz_localize(
                "UTC"
            )
        )
    else:
        reference_timestamp = (
            reference_timestamp.tz_convert(
                "UTC"
            )
        )

    age_days = (
        reference_timestamp
        - latest_date
    ).total_seconds() / 86400.0

    if age_days <= stale_after_days:
        return []

    return [
        DataQualityFinding(
            category="Freshness",
            severity="Medium",
            dataset=dataset,
            field_name=date_column,
            finding=(
                "Operational data may be stale."
            ),
            affected_records=len(
                dataframe
            ),
            evidence=(
                f"Latest '{date_column}' date is "
                f"{latest_date.date()}; "
                f"data age is {age_days:.1f} days; "
                f"configured threshold is "
                f"{stale_after_days} days."
            ),
        )
    ]