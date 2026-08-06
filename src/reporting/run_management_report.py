"""Run the aviation spare-parts management report export."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.dashboards.data_access import DashboardRepository
from src.reporting.management_report import (
    generate_management_report,
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
    """Generate the management Excel report."""

    settings = load_settings()

    report_settings = settings[
        "reporting"
    ][
        "management_report"
    ]

    if not bool(
        report_settings["enabled"]
    ):
        print(
            "Management-report generation is disabled."
        )
        return

    database_path = (
        PROJECT_ROOT
        / settings["paths"]["database"]
    )

    reports_directory = (
        PROJECT_ROOT
        / settings["paths"]["reports"]
    )

    output_path = (
        reports_directory
        / report_settings[
            "output_filename"
        ]
    )

    repository = DashboardRepository(
        database_path
    )

    generated_path = generate_management_report(
        repository=repository,
        database_path=database_path,
        output_path=output_path,
        report_settings=report_settings,
    )

    print("=" * 72)
    print(
        "AVIATION SPARE PARTS — "
        "MANAGEMENT REPORT EXPORT"
    )
    print("=" * 72)
    print(
        f"Report created: {generated_path}"
    )
    print(
        "Report format: Microsoft Excel"
    )
    print(
        "Automatic purchasing enabled: False"
    )
    print(
        "Human approval required: True"
    )
    print("=" * 72)


if __name__ == "__main__":
    main()