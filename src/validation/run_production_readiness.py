"""Run final production-readiness validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from src.validation.production_readiness import (
    check_database_exists,
    check_governance,
    check_latest_pipeline,
    check_management_report,
    check_required_tables,
    check_scheduled_job_summary,
    check_scheduled_lock,
    determine_overall_status,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


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


def main() -> None:
    """Run the final system-readiness checks."""

    settings = load_settings()

    readiness_settings = settings[
        "production_readiness"
    ]

    if not bool(
        readiness_settings["enabled"]
    ):
        print(
            "Production-readiness validation is disabled."
        )
        return

    database_path = (
        PROJECT_ROOT
        / settings["paths"]["database"]
    )

    scheduled_summary_path = (
        PROJECT_ROOT
        / settings["scheduling"][
            "latest_summary"
        ]
    )

    lock_path = (
        PROJECT_ROOT
        / settings["scheduling"][
            "lock_file"
        ]
    )

    report_path = (
        PROJECT_ROOT
        / settings["paths"]["reports"]
        / settings["reporting"][
            "management_report"
        ][
            "output_filename"
        ]
    )

    checks = [
        check_database_exists(
            database_path
        ),
        *check_required_tables(
            database_path,
            list(
                readiness_settings[
                    "required_tables"
                ]
            ),
        ),
        check_latest_pipeline(
            database_path
        ),
        check_scheduled_job_summary(
            scheduled_summary_path
        ),
        check_management_report(
            report_path
        ),
        check_scheduled_lock(
            lock_path
        ),
        *check_governance(
            settings
        ),
    ]

    overall_status = (
        determine_overall_status(
            checks
        )
    )

    separator = "=" * 72

    print(separator)
    print(
        "AVIATION SPARE PARTS — "
        "PRODUCTION READINESS"
    )
    print(separator)

    for check in checks:
        icon = (
            "✓"
            if check.status == "Passed"
            else "✗"
        )

        print(
            f"{icon} {check.check_name}: "
            f"{check.status}"
        )

        print(
            f"  {check.message}"
        )

    print(separator)

    print(
        "PRODUCTION READINESS: "
        f"{overall_status.upper()}"
    )

    print(separator)

    output_path = (
        PROJECT_ROOT
        / settings["paths"]["reports"]
        / "production_readiness_summary.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            {
                "overall_status": (
                    overall_status
                ),
                "checks": [
                    check.to_dict()
                    for check in checks
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Summary: {output_path}"
    )

    if overall_status != "Passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()