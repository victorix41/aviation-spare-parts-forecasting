"""Tests for the production-readiness dashboard helpers."""

from __future__ import annotations

import json
from pathlib import Path

from src.dashboards.production_readiness_dashboard import (
    load_production_readiness_summary,
    readiness_checks_frame,
)


def test_load_production_readiness_summary(
    tmp_path: Path,
) -> None:
    """Valid readiness summary loads successfully."""

    summary_path = (
        tmp_path
        / "production_readiness_summary.json"
    )

    summary_path.write_text(
        json.dumps(
            {
                "overall_status": "Passed",
                "checks": [],
            }
        ),
        encoding="utf-8",
    )

    result = (
        load_production_readiness_summary(
            summary_path
        )
    )

    assert result is not None
    assert result["overall_status"] == "Passed"


def test_missing_readiness_summary_returns_none(
    tmp_path: Path,
) -> None:
    """Missing readiness summary is handled safely."""

    result = (
        load_production_readiness_summary(
            tmp_path
            / "missing.json"
        )
    )

    assert result is None


def test_invalid_readiness_summary_returns_none(
    tmp_path: Path,
) -> None:
    """Invalid JSON is handled safely."""

    summary_path = (
        tmp_path
        / "production_readiness_summary.json"
    )

    summary_path.write_text(
        "not-json",
        encoding="utf-8",
    )

    result = (
        load_production_readiness_summary(
            summary_path
        )
    )

    assert result is None


def test_readiness_checks_frame() -> None:
    """Readiness checks convert to tabular form."""

    summary = {
        "checks": [
            {
                "check_name": "Agent assurance",
                "status": "Passed",
                "message": (
                    "Agent assurance evidence passed."
                ),
            },
            {
                "check_name": "Decision audit",
                "status": "Passed",
                "message": (
                    "Decision-audit store is available."
                ),
            },
        ]
    }

    result = readiness_checks_frame(
        summary
    )

    assert len(result) == 2

    assert list(
        result.columns
    ) == [
        "check_name",
        "status",
        "message",
    ]

    assert (
        result.iloc[0]["check_name"]
        == "Agent assurance"
    )


def test_invalid_checks_return_empty_frame() -> None:
    """Malformed checks are handled safely."""

    result = readiness_checks_frame(
        {
            "checks": "invalid",
        }
    )

    assert result.empty