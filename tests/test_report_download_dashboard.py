"""Tests for dashboard management-report downloads."""

from datetime import datetime
from pathlib import Path

import pytest

from src.dashboards.report_download_dashboard import (
    create_download_filename,
    read_report_bytes,
)


def test_create_download_filename() -> None:
    """A timestamp should be added to the workbook name."""

    generated_at = datetime(
        2026,
        8,
        6,
        20,
        30,
        45,
    )

    result = create_download_filename(
        "aviation_report.xlsx",
        generated_at,
    )

    assert result == (
        "aviation_report_"
        "20260806_203045.xlsx"
    )


def test_create_download_filename_adds_extension() -> None:
    """A missing extension should default to XLSX."""

    generated_at = datetime(
        2026,
        8,
        6,
        20,
        30,
        45,
    )

    result = create_download_filename(
        "aviation_report",
        generated_at,
    )

    assert result.endswith(
        ".xlsx"
    )


def test_read_report_bytes(
    tmp_path: Path,
) -> None:
    """A generated report should be returned as bytes."""

    report_path = (
        tmp_path
        / "report.xlsx"
    )

    report_path.write_bytes(
        b"example workbook bytes"
    )

    result = read_report_bytes(
        report_path
    )

    assert result == (
        b"example workbook bytes"
    )


def test_read_report_bytes_missing_file(
    tmp_path: Path,
) -> None:
    """A missing report should raise a readable error."""

    with pytest.raises(
        FileNotFoundError,
        match="not found",
    ):
        read_report_bytes(
            tmp_path
            / "missing.xlsx"
        )