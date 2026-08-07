"""Tests for scheduled-job monitoring."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import json

from src.scheduling.job_monitoring import (
    determine_scheduled_job_freshness,
    inspect_job_lock,
    load_recent_job_logs,
    load_scheduled_job_summary,
    scheduled_job_stages_frame,
)


def test_load_scheduled_job_summary(
    tmp_path: Path,
) -> None:
    """A valid JSON summary should be loaded."""

    summary_path = (
        tmp_path
        / "summary.json"
    )

    summary_path.write_text(
        json.dumps(
            {
                "job_run_id": "JOB-001",
                "overall_status": "Passed",
                "stages": [],
            }
        ),
        encoding="utf-8",
    )

    summary = load_scheduled_job_summary(
        summary_path
    )

    assert summary is not None
    assert summary["job_run_id"] == "JOB-001"


def test_missing_summary_returns_none(
    tmp_path: Path,
) -> None:
    """A missing summary should not raise an error."""

    result = load_scheduled_job_summary(
        tmp_path
        / "missing.json"
    )

    assert result is None


def test_scheduled_job_stages_frame() -> None:
    """Scheduled stages should become tabular data."""

    dataframe = scheduled_job_stages_frame(
        {
            "stages": [
                {
                    "module_name": (
                        "src.pipeline."
                        "run_full_pipeline"
                    ),
                    "status": "Passed",
                    "return_code": 0,
                    "duration_seconds": 4.5,
                }
            ]
        }
    )

    assert len(dataframe) == 1

    assert (
        dataframe.iloc[0][
            "status"
        ]
        == "Passed"
    )


def test_scheduled_job_freshness_current() -> None:
    """A recent job should be current."""

    completed_at = (
        datetime.now(UTC)
        - timedelta(hours=2)
    )

    status, age_hours = (
        determine_scheduled_job_freshness(
            completed_at=completed_at,
            stale_after_hours=24,
        )
    )

    assert status == "Current"
    assert 1.0 < age_hours < 3.0


def test_scheduled_job_freshness_stale() -> None:
    """An old job should be stale."""

    completed_at = (
        datetime.now(UTC)
        - timedelta(hours=30)
    )

    status, age_hours = (
        determine_scheduled_job_freshness(
            completed_at=completed_at,
            stale_after_hours=24,
        )
    )

    assert status == "Stale"
    assert age_hours > 24


def test_recent_job_logs(
    tmp_path: Path,
) -> None:
    """Only the requested recent log files should be returned."""

    for index in range(3):
        log_path = (
            tmp_path
            / f"scheduled_job_{index}.log"
        )

        log_path.write_text(
            f"Log {index}",
            encoding="utf-8",
        )

    dataframe = load_recent_job_logs(
        tmp_path,
        limit=2,
    )

    assert len(dataframe) == 2


def test_missing_lock_file(
    tmp_path: Path,
) -> None:
    """A missing lock should be reported clearly."""

    result = inspect_job_lock(
        tmp_path
        / "missing.lock",
        stale_after_minutes=60,
    )

    assert result["exists"] is False
    assert result["status"] == "Not present"