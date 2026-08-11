"""Tests for management data-quality monitoring."""

import pandas as pd

from src.validation.data_quality_monitoring import (
    check_duplicate_keys,
    check_negative_values,
    check_required_columns,
    check_required_values,
    summarise_data_quality,
)


def test_missing_required_column_is_critical() -> None:
    """Missing schema field should be critical."""

    dataframe = pd.DataFrame(
        {
            "part_number": [
                "PN-001",
            ],
        }
    )

    findings = check_required_columns(
        dataframe=dataframe,
        dataset="inventory",
        required_columns=[
            "part_number",
            "description",
        ],
    )

    assert len(findings) == 1
    assert findings[0].severity == "Critical"


def test_missing_required_value_is_high() -> None:
    """Missing required data should be high severity."""

    dataframe = pd.DataFrame(
        {
            "part_number": [
                "PN-001",
                None,
            ],
        }
    )

    findings = check_required_values(
        dataframe=dataframe,
        dataset="inventory",
        required_columns=[
            "part_number",
        ],
    )

    assert len(findings) == 1
    assert findings[0].affected_records == 1


def test_duplicate_business_key_is_detected() -> None:
    """Duplicate keys should be detected."""

    dataframe = pd.DataFrame(
        {
            "part_number": [
                "PN-001",
                "PN-001",
            ],
        }
    )

    findings = check_duplicate_keys(
        dataframe=dataframe,
        dataset="inventory",
        key_columns=[
            "part_number",
        ],
    )

    assert len(findings) == 1
    assert findings[0].affected_records == 2


def test_negative_value_is_detected() -> None:
    """Negative quantities should be detected."""

    dataframe = pd.DataFrame(
        {
            "quantity_issued": [
                1,
                -2,
            ],
        }
    )

    findings = check_negative_values(
        dataframe=dataframe,
        dataset="issue_history",
        numeric_columns=[
            "quantity_issued",
        ],
    )

    assert len(findings) == 1
    assert findings[0].affected_records == 1


def test_clean_data_quality_passes() -> None:
    """No findings should produce Passed status."""

    summary = summarise_data_quality(
        []
    )

    assert (
        summary["status"]
        == "Passed"
    )