"""Run the scheduled aviation spare-parts processing job."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def load_settings() -> dict[str, Any]:
    """Load project settings."""

    settings_path = (
        PROJECT_ROOT
        / "config"
        / "settings.yaml"
    )

    with settings_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        settings = yaml.safe_load(file)

    if not isinstance(settings, dict):
        raise ValueError(
            "Project settings must be a YAML mapping."
        )

    return settings


def acquire_lock(lock_path: Path) -> int:
    """Create an exclusive lock file and return its file descriptor."""

    lock_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        descriptor = os.open(
            lock_path,
            os.O_CREAT
            | os.O_EXCL
            | os.O_WRONLY,
        )
    except FileExistsError as exc:
        raise RuntimeError(
            "Another scheduled job appears to be running. "
            f"Lock file: {lock_path}"
        ) from exc

    lock_content = {
        "process_id": os.getpid(),
        "created_at": utc_timestamp(),
    }

    os.write(
        descriptor,
        json.dumps(
            lock_content,
            indent=2,
        ).encode("utf-8"),
    )

    return descriptor


def release_lock(
    lock_path: Path,
    descriptor: int | None,
) -> None:
    """Release a lock only when this process acquired it."""

    if descriptor is None:
        return

    try:
        os.close(descriptor)
    except OSError:
        pass

    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def run_module(
    module_name: str,
) -> dict[str, Any]:
    """Run one project module and capture its result."""

    started_at = utc_timestamp()
    timer = perf_counter()

    process = subprocess.run(
        [
            sys.executable,
            "-m",
            module_name,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    duration_seconds = (
        perf_counter()
        - timer
    )

    completed_at = utc_timestamp()

    return {
        "module_name": module_name,
        "status": (
            "Passed"
            if process.returncode == 0
            else "Failed"
        ),
        "return_code": int(
            process.returncode
        ),
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": float(
            duration_seconds
        ),
        "standard_output": (
            process.stdout.strip()
        ),
        "standard_error": (
            process.stderr.strip()
        ),
    }


def write_job_log(
    log_path: Path,
    summary: dict[str, Any],
) -> None:
    """Write a readable scheduled-job execution log."""

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lines = [
        "=" * 72,
        "AVIATION SPARE PARTS — SCHEDULED JOB",
        "=" * 72,
        f"Job run ID: {summary['job_run_id']}",
        f"Started at: {summary['started_at']}",
        f"Completed at: {summary['completed_at']}",
        f"Overall status: {summary['overall_status']}",
        (
            "Duration: "
            f"{summary['duration_seconds']:.2f} seconds"
        ),
        "",
    ]

    for stage in summary["stages"]:
        lines.extend(
            [
                "-" * 72,
                f"Module: {stage['module_name']}",
                f"Status: {stage['status']}",
                (
                    "Duration: "
                    f"{stage['duration_seconds']:.2f} seconds"
                ),
                f"Return code: {stage['return_code']}",
            ]
        )

        if stage["standard_output"]:
            lines.extend(
                [
                    "",
                    "Standard output:",
                    stage["standard_output"],
                ]
            )

        if stage["standard_error"]:
            lines.extend(
                [
                    "",
                    "Standard error:",
                    stage["standard_error"],
                ]
            )

        lines.append("")

    log_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def remove_old_logs(
    log_directory: Path,
    maximum_log_files: int,
) -> None:
    """Retain only the configured number of recent logs."""

    if maximum_log_files < 1:
        return

    log_files = sorted(
        log_directory.glob(
            "scheduled_job_*.log"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    for old_file in log_files[
        maximum_log_files:
    ]:
        old_file.unlink(
            missing_ok=True
        )


def save_summary(
    summary_path: Path,
    summary: dict[str, Any],
) -> None:
    """Save the latest scheduled-job summary."""

    summary_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    """Run the scheduled pipeline and report workflow."""

    settings = load_settings()

    scheduling_settings = settings[
        "scheduling"
    ]

    if not bool(
        scheduling_settings["enabled"]
    ):
        print(
            "Scheduled execution is disabled."
        )
        return

    lock_path = (
        PROJECT_ROOT
        / scheduling_settings[
            "lock_file"
        ]
    )

    summary_path = (
        PROJECT_ROOT
        / scheduling_settings[
            "latest_summary"
        ]
    )

    log_directory = (
        PROJECT_ROOT
        / scheduling_settings[
            "log_directory"
        ]
    )

    maximum_log_files = int(
        scheduling_settings[
            "retention"
        ][
            "maximum_log_files"
        ]
    )

    job_run_id = (
        f"JOB-{uuid.uuid4().hex[:12].upper()}"
    )

    started_at = utc_timestamp()
    timer = perf_counter()

    lock_descriptor: int | None = None
    stages: list[dict[str, Any]] = []

    try:
        lock_descriptor = acquire_lock(
            lock_path
        )

        if bool(
            scheduling_settings[
                "run_pipeline"
            ]
        ):
            pipeline_result = run_module(
                "src.pipeline.run_full_pipeline"
            )

            stages.append(
                pipeline_result
            )

            if (
                pipeline_result["status"]
                == "Failed"
                and bool(
                    scheduling_settings[
                        "stop_report_when_pipeline_fails"
                    ]
                )
            ):
                raise RuntimeError(
                    "The full pipeline failed. "
                    "Management-report generation was stopped."
                )

        if bool(
            scheduling_settings[
                "generate_management_report"
            ]
        ):
            report_result = run_module(
                "src.reporting.run_management_report"
            )

            stages.append(
                report_result
            )

            if (
                report_result["status"]
                == "Failed"
            ):
                raise RuntimeError(
                    "Management-report generation failed."
                )

        overall_status = (
            "Passed"
            if all(
                stage["status"] == "Passed"
                for stage in stages
            )
            else "Failed"
        )

        error_message = None

    except Exception as exc:
        overall_status = "Failed"
        error_message = str(exc)

    finally:
        completed_at = utc_timestamp()

        duration_seconds = (
            perf_counter()
            - timer
        )

        summary = {
            "job_run_id": job_run_id,
            "job_name": scheduling_settings[
                "job_name"
            ],
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_seconds": float(
                duration_seconds
            ),
            "overall_status": overall_status,
            "error_message": error_message,
            "stages": stages,
        }

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        log_path = (
            log_directory
            / f"scheduled_job_{timestamp}.log"
        )

        save_summary(
            summary_path,
            summary,
        )

        write_job_log(
            log_path,
            summary,
        )

        remove_old_logs(
            log_directory,
            maximum_log_files,
        )

        release_lock(
            lock_path,
            lock_descriptor,
        )

    print("=" * 72)
    print(
        "AVIATION SPARE PARTS — "
        "SCHEDULED EXECUTION"
    )
    print("=" * 72)
    print(
        f"Job run ID: {job_run_id}"
    )
    print(
        f"Overall status: {overall_status}"
    )
    print(
        f"Stages completed: {len(stages)}"
    )
    print(
        f"Duration: {duration_seconds:.2f} seconds"
    )
    print(
        f"Summary: {summary_path}"
    )
    print(
        f"Log: {log_path}"
    )
    print("=" * 72)

    if overall_status != "Passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()