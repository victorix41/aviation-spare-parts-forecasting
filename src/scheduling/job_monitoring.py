"""Scheduled-job monitoring utilities."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


def load_scheduled_job_summary(
    summary_path: Path,
) -> dict[str, Any] | None:
    """Load the latest scheduled-job JSON summary."""

    if not summary_path.is_file():
        return None

    try:
        content = summary_path.read_text(
            encoding="utf-8"
        )

        result = json.loads(content)

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError(
            "The scheduled-job summary could not be read: "
            f"{summary_path}"
        ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            "The scheduled-job summary must contain "
            "a JSON object."
        )

    return result


def scheduled_job_stages_frame(
    summary: dict[str, Any] | None,
) -> pd.DataFrame:
    """Convert scheduled-job stages into a DataFrame."""

    expected_columns = [
        "module_name",
        "status",
        "return_code",
        "started_at",
        "completed_at",
        "duration_seconds",
        "standard_output",
        "standard_error",
    ]

    if not summary:
        return pd.DataFrame(
            columns=expected_columns
        )

    stages = summary.get(
        "stages",
        [],
    )

    if not isinstance(stages, list):
        return pd.DataFrame(
            columns=expected_columns
        )

    dataframe = pd.DataFrame(
        stages
    )

    for column in expected_columns:
        if column not in dataframe.columns:
            dataframe[column] = None

    return dataframe[
        expected_columns
    ]


def determine_scheduled_job_freshness(
    *,
    completed_at: object,
    stale_after_hours: float,
) -> tuple[str, float]:
    """Determine whether a scheduled-job result is stale."""

    completed_timestamp = pd.to_datetime(
        completed_at,
        errors="coerce",
        utc=True,
    )

    if pd.isna(completed_timestamp):
        return (
            "Unknown",
            0.0,
        )

    current_timestamp = pd.Timestamp.now(
        tz="UTC"
    )

    age_hours = float(
        (
            current_timestamp
            - completed_timestamp
        ).total_seconds()
        / 3600
    )

    status = (
        "Stale"
        if age_hours > float(stale_after_hours)
        else "Current"
    )

    return (
        status,
        age_hours,
    )


def load_recent_job_logs(
    log_directory: Path,
    *,
    limit: int,
) -> pd.DataFrame:
    """Load metadata for recent scheduled-job log files."""

    columns = [
        "log_filename",
        "modified_at",
        "size_bytes",
        "log_path",
    ]

    if not log_directory.is_dir():
        return pd.DataFrame(
            columns=columns
        )

    log_files = sorted(
        log_directory.glob(
            "scheduled_job_*.log"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    rows: list[dict[str, object]] = []

    for log_path in log_files[
        : max(int(limit), 0)
    ]:
        metadata = log_path.stat()

        rows.append(
            {
                "log_filename": log_path.name,
                "modified_at": datetime.fromtimestamp(
                    metadata.st_mtime,
                    tz=UTC,
                ),
                "size_bytes": int(
                    metadata.st_size
                ),
                "log_path": str(
                    log_path
                ),
            }
        )

    return pd.DataFrame(
        rows,
        columns=columns,
    )


def read_job_log(
    log_path: Path,
) -> str:
    """Read one scheduled-job log."""

    if not log_path.is_file():
        raise FileNotFoundError(
            f"Scheduled-job log was not found: {log_path}"
        )

    return log_path.read_text(
        encoding="utf-8"
    )


def inspect_job_lock(
    lock_path: Path,
    *,
    stale_after_minutes: float,
) -> dict[str, object]:
    """Inspect the scheduled-job lock file."""

    if not lock_path.is_file():
        return {
            "exists": False,
            "status": "Not present",
            "age_minutes": 0.0,
            "process_id": None,
            "created_at": None,
        }

    metadata = lock_path.stat()

    modified_at = datetime.fromtimestamp(
        metadata.st_mtime,
        tz=UTC,
    )

    current_time = datetime.now(
        UTC
    )

    age_minutes = (
        current_time
        - modified_at
    ).total_seconds() / 60

    process_id = None
    created_at = None

    try:
        content = json.loads(
            lock_path.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(content, dict):
            process_id = content.get(
                "process_id"
            )

            created_at = content.get(
                "created_at"
            )

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    status = (
        "Stale"
        if age_minutes
        > float(stale_after_minutes)
        else "Active"
    )

    return {
        "exists": True,
        "status": status,
        "age_minutes": float(
            age_minutes
        ),
        "process_id": process_id,
        "created_at": created_at,
    }