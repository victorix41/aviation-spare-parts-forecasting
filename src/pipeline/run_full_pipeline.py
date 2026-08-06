"""Run the complete aviation spare-parts processing pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import duckdb
import pandas as pd
import yaml

from src.pipeline.pipeline_models import (
    PipelineRunSummary,
    PipelineStageResult,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


PIPELINE_STAGES = [
    (
        "Data ingestion and validation",
        "src.data.ingestion_pipeline",
    ),
    (
        "Demand analytics",
        "src.analytics.run_demand_analysis",
    ),
    (
        "Forecast model selection",
        "src.forecasting.run_model_selection",
    ),
    (
        "Inventory optimisation",
        "src.optimisation.run_inventory_optimisation",
    ),
    (
        "Agentic advisory generation",
        "src.agents.run_advisory_engine",
    ),
]


def utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(
        UTC
    ).isoformat()


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


def run_stage(
    stage_name: str,
    module_name: str,
) -> PipelineStageResult:
    """Execute one Python module as a pipeline stage."""

    started_at = utc_timestamp()
    timer_start = perf_counter()

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

    completed_at = utc_timestamp()
    duration_seconds = (
        perf_counter()
        - timer_start
    )

    if process.stdout:
        print(process.stdout)

    if process.stderr:
        print(
            process.stderr,
            file=sys.stderr,
        )

    error_message = None

    if process.returncode != 0:
        error_message = (
            process.stderr.strip()
            or process.stdout.strip()
            or "Stage failed without an error message."
        )

    return PipelineStageResult(
        stage_name=stage_name,
        module_name=module_name,
        status=(
            "Passed"
            if process.returncode == 0
            else "Failed"
        ),
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=float(
            duration_seconds
        ),
        return_code=int(
            process.returncode
        ),
        error_message=error_message,
    )


def save_summary_json(
    summary: PipelineRunSummary,
    reports_directory: Path,
) -> Path:
    """Save the pipeline summary as JSON."""

    reports_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        reports_directory
        / "full_pipeline_summary.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary.to_dict(),
            file,
            indent=2,
        )

    return output_path


def write_pipeline_metadata(
    summary: PipelineRunSummary,
    database_path: Path,
) -> None:
    """Write pipeline-run metadata to DuckDB."""

    run_frame = pd.DataFrame(
        [
            {
                "pipeline_run_id": (
                    summary.pipeline_run_id
                ),
                "started_at": summary.started_at,
                "completed_at": (
                    summary.completed_at
                ),
                "duration_seconds": (
                    summary.duration_seconds
                ),
                "overall_status": (
                    summary.overall_status
                ),
                "successful_stage_count": (
                    summary.successful_stage_count
                ),
                "failed_stage_count": (
                    summary.failed_stage_count
                ),
            }
        ]
    )

    stage_frame = pd.DataFrame(
        [
            {
                "pipeline_run_id": (
                    summary.pipeline_run_id
                ),
                **stage.to_dict(),
            }
            for stage in summary.stages
        ]
    )

    with duckdb.connect(
        str(database_path)
    ) as connection:
        connection.register(
            "pipeline_run_frame",
            run_frame,
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pipeline_runs AS
            SELECT *
            FROM pipeline_run_frame
            WHERE FALSE
            """
        )

        connection.execute(
            """
            INSERT INTO pipeline_runs
            SELECT *
            FROM pipeline_run_frame
            """
        )

        connection.unregister(
            "pipeline_run_frame"
        )

        connection.register(
            "pipeline_stage_frame",
            stage_frame,
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pipeline_stage_runs AS
            SELECT *
            FROM pipeline_stage_frame
            WHERE FALSE
            """
        )

        connection.execute(
            """
            INSERT INTO pipeline_stage_runs
            SELECT *
            FROM pipeline_stage_frame
            """
        )

        connection.unregister(
            "pipeline_stage_frame"
        )


def main() -> None:
    """Run every processing stage in sequence."""

    settings = load_settings()

    pipeline_run_id = (
        f"RUN-{uuid.uuid4().hex[:12].upper()}"
    )

    pipeline_started_at = utc_timestamp()
    pipeline_timer = perf_counter()

    results: list[
        PipelineStageResult
    ] = []

    separator = "=" * 72

    print(separator)
    print(
        "AVIATION SPARE PARTS — "
        "END-TO-END PIPELINE"
    )
    print(separator)
    print(
        f"Pipeline run ID: {pipeline_run_id}"
    )

    for stage_number, (
        stage_name,
        module_name,
    ) in enumerate(
        PIPELINE_STAGES,
        start=1,
    ):
        print()
        print(
            f"[{stage_number}/{len(PIPELINE_STAGES)}] "
            f"{stage_name}"
        )
        print("-" * 72)

        result = run_stage(
            stage_name,
            module_name,
        )

        results.append(
            result
        )

        print(
            f"Stage status: {result.status}"
        )

        print(
            "Stage duration: "
            f"{result.duration_seconds:.2f} seconds"
        )

        if result.status == "Failed":
            print(
                "Pipeline stopped because the stage failed."
            )
            break

    pipeline_completed_at = utc_timestamp()

    duration_seconds = (
        perf_counter()
        - pipeline_timer
    )

    successful_count = sum(
        result.status == "Passed"
        for result in results
    )

    failed_count = sum(
        result.status == "Failed"
        for result in results
    )

    overall_status = (
        "Passed"
        if (
            failed_count == 0
            and len(results)
            == len(PIPELINE_STAGES)
        )
        else "Failed"
    )

    summary = PipelineRunSummary(
        pipeline_run_id=pipeline_run_id,
        started_at=pipeline_started_at,
        completed_at=pipeline_completed_at,
        duration_seconds=float(
            duration_seconds
        ),
        overall_status=overall_status,
        successful_stage_count=int(
            successful_count
        ),
        failed_stage_count=int(
            failed_count
        ),
        stages=results,
    )

    reports_directory = (
        PROJECT_ROOT
        / settings["paths"]["reports"]
    )

    database_path = (
        PROJECT_ROOT
        / settings["paths"]["database"]
    )

    summary_path = save_summary_json(
        summary,
        reports_directory,
    )

    if database_path.is_file():
        write_pipeline_metadata(
            summary,
            database_path,
        )

    print()
    print(separator)
    print(
        f"Overall pipeline status: "
        f"{summary.overall_status}"
    )
    print(
        f"Successful stages: "
        f"{summary.successful_stage_count}"
    )
    print(
        f"Failed stages: "
        f"{summary.failed_stage_count}"
    )
    print(
        f"Total duration: "
        f"{summary.duration_seconds:.2f} seconds"
    )
    print(
        f"Summary file: {summary_path}"
    )
    print(separator)

    if overall_status != "Passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()