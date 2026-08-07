"""Tests for scheduled pipeline and report execution."""

from pathlib import Path

import pytest

from src.scheduling.run_scheduled_job import (
    acquire_lock,
    release_lock,
    remove_old_logs,
)


def test_lock_file_creation_and_release(
    tmp_path: Path,
) -> None:
    """A job lock should be created and removed."""

    lock_path = (
        tmp_path
        / "scheduled_job.lock"
    )

    descriptor = acquire_lock(
        lock_path
    )

    assert lock_path.is_file()

    release_lock(
        lock_path,
        descriptor,
    )

    assert not lock_path.exists()


def test_duplicate_lock_is_rejected(
    tmp_path: Path,
) -> None:
    """A second scheduled run should be rejected."""

    lock_path = (
        tmp_path
        / "scheduled_job.lock"
    )

    descriptor = acquire_lock(
        lock_path
    )

    try:
        with pytest.raises(
            RuntimeError,
            match="appears to be running",
        ):
            acquire_lock(
                lock_path
            )
    finally:
        release_lock(
            lock_path,
            descriptor,
        )


def test_old_logs_are_removed(
    tmp_path: Path,
) -> None:
    """Only the configured number of logs should remain."""

    log_directory = (
        tmp_path
        / "logs"
    )

    log_directory.mkdir()

    for index in range(5):
        log_path = (
            log_directory
            / f"scheduled_job_{index}.log"
        )

        log_path.write_text(
            str(index),
            encoding="utf-8",
        )

    remove_old_logs(
        log_directory,
        maximum_log_files=2,
    )

    remaining_logs = list(
        log_directory.glob(
            "scheduled_job_*.log"
        )
    )

    assert len(remaining_logs) == 2