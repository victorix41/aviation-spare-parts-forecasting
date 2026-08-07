"""Production-readiness validation for the aviation spare-parts platform."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import duckdb


@dataclass(frozen=True)
class ReadinessCheck:
    """Result of one production-readiness check."""

    check_name: str
    status: str
    message: str

    def to_dict(self) -> dict[str, str]:
        """Return a serialisable result."""

        return asdict(self)


def check_database_exists(
    database_path: Path,
) -> ReadinessCheck:
    """Confirm that the DuckDB database exists."""

    if database_path.is_file():
        return ReadinessCheck(
            check_name="Database exists",
            status="Passed",
            message=str(database_path),
        )

    return ReadinessCheck(
        check_name="Database exists",
        status="Failed",
        message=(
            f"Database was not found: {database_path}"
        ),
    )


def check_required_tables(
    database_path: Path,
    required_tables: list[str],
) -> list[ReadinessCheck]:
    """Confirm required DuckDB tables exist and contain data."""

    if not database_path.is_file():
        return [
            ReadinessCheck(
                check_name="Required tables",
                status="Failed",
                message="Database is unavailable.",
            )
        ]

    checks: list[ReadinessCheck] = []

    with duckdb.connect(
        str(database_path),
        read_only=True,
    ) as connection:
        available_tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                """
            ).fetchall()
        }

        for table_name in required_tables:
            if table_name not in available_tables:
                checks.append(
                    ReadinessCheck(
                        check_name=(
                            f"Table: {table_name}"
                        ),
                        status="Failed",
                        message="Table is missing.",
                    )
                )
                continue

            row_count = int(
                connection.execute(
                    f'''
                    SELECT COUNT(*)
                    FROM "{table_name}"
                    '''
                ).fetchone()[0]
            )

            checks.append(
                ReadinessCheck(
                    check_name=(
                        f"Table: {table_name}"
                    ),
                    status=(
                        "Passed"
                        if row_count > 0
                        else "Failed"
                    ),
                    message=(
                        f"{row_count:,} records"
                        if row_count > 0
                        else "Table is empty."
                    ),
                )
            )

    return checks


def check_latest_pipeline(
    database_path: Path,
) -> ReadinessCheck:
    """Confirm that the latest end-to-end pipeline passed."""

    if not database_path.is_file():
        return ReadinessCheck(
            check_name="Latest pipeline",
            status="Failed",
            message="Database is unavailable.",
        )

    try:
        with duckdb.connect(
            str(database_path),
            read_only=True,
        ) as connection:
            row = connection.execute(
                """
                SELECT
                    pipeline_run_id,
                    overall_status,
                    successful_stage_count,
                    failed_stage_count
                FROM pipeline_runs
                ORDER BY completed_at DESC
                LIMIT 1
                """
            ).fetchone()

    except duckdb.Error as exc:
        return ReadinessCheck(
            check_name="Latest pipeline",
            status="Failed",
            message=str(exc),
        )

    if row is None:
        return ReadinessCheck(
            check_name="Latest pipeline",
            status="Failed",
            message="No pipeline run is available.",
        )

    run_id, status, passed, failed = row

    return ReadinessCheck(
        check_name="Latest pipeline",
        status=(
            "Passed"
            if status == "Passed"
            and int(failed) == 0
            else "Failed"
        ),
        message=(
            f"{run_id}: {status}; "
            f"{passed} passed, {failed} failed"
        ),
    )


def check_scheduled_job_summary(
    summary_path: Path,
) -> ReadinessCheck:
    """Confirm the latest scheduled workflow passed."""

    if not summary_path.is_file():
        return ReadinessCheck(
            check_name="Scheduled job",
            status="Failed",
            message=(
                f"Summary not found: {summary_path}"
            ),
        )

    try:
        summary = json.loads(
            summary_path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        return ReadinessCheck(
            check_name="Scheduled job",
            status="Failed",
            message=str(exc),
        )

    status = str(
        summary.get(
            "overall_status",
            "Unknown",
        )
    )

    run_id = str(
        summary.get(
            "job_run_id",
            "Unavailable",
        )
    )

    return ReadinessCheck(
        check_name="Scheduled job",
        status=(
            "Passed"
            if status == "Passed"
            else "Failed"
        ),
        message=f"{run_id}: {status}",
    )


def check_management_report(
    report_path: Path,
) -> ReadinessCheck:
    """Confirm that the management workbook exists."""

    if not report_path.is_file():
        return ReadinessCheck(
            check_name="Management report",
            status="Failed",
            message=(
                f"Report not found: {report_path}"
            ),
        )

    size_bytes = report_path.stat().st_size

    return ReadinessCheck(
        check_name="Management report",
        status=(
            "Passed"
            if size_bytes > 0
            else "Failed"
        ),
        message=f"{size_bytes:,} bytes",
    )


def check_scheduled_lock(
    lock_path: Path,
) -> ReadinessCheck:
    """Confirm no scheduled execution lock remains."""

    if lock_path.exists():
        return ReadinessCheck(
            check_name="Scheduled-job lock",
            status="Failed",
            message=(
                f"Lock file still exists: {lock_path}"
            ),
        )

    return ReadinessCheck(
        check_name="Scheduled-job lock",
        status="Passed",
        message="No active lock file.",
    )


def check_governance(
    settings: dict[str, Any],
) -> list[ReadinessCheck]:
    """Validate mandatory governance controls."""

    inventory_governance = settings[
        "inventory_optimisation"
    ][
        "governance"
    ]

    agent_governance = settings[
        "agentic_ai"
    ][
        "governance"
    ]

    dashboard_governance = settings[
        "dashboard"
    ][
        "governance"
    ]

    return [
        ReadinessCheck(
            check_name="Human approval required",
            status=(
                "Passed"
                if bool(
                    inventory_governance[
                        "human_approval_required"
                    ]
                )
                and bool(
                    agent_governance[
                        "require_human_approval"
                    ]
                )
                and bool(
                    dashboard_governance[
                        "require_human_approval"
                    ]
                )
                else "Failed"
            ),
            message=(
                "Human approval remains mandatory."
            ),
        ),
        ReadinessCheck(
            check_name="Automatic purchasing disabled",
            status=(
                "Passed"
                if not bool(
                    inventory_governance[
                        "automatic_purchase_orders"
                    ]
                )
                and not bool(
                    agent_governance[
                        "allow_purchase_order_creation"
                    ]
                )
                and not bool(
                    dashboard_governance[
                        "allow_purchase_order_creation"
                    ]
                )
                else "Failed"
            ),
            message=(
                "Automatic purchase-order creation "
                "is disabled."
            ),
        ),
        ReadinessCheck(
            check_name="Inventory write-back disabled",
            status=(
                "Passed"
                if not bool(
                    agent_governance[
                        "allow_inventory_changes"
                    ]
                )
                and not bool(
                    dashboard_governance[
                        "allow_inventory_updates"
                    ]
                )
                else "Failed"
            ),
            message=(
                "Inventory write-back is disabled."
            ),
        ),
    ]


def determine_overall_status(
    checks: list[ReadinessCheck],
) -> str:
    """Determine the overall production-readiness result."""

    return (
        "Passed"
        if all(
            check.status == "Passed"
            for check in checks
        )
        else "Failed"
    )