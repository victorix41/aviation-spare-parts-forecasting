"""Run final production-readiness validation."""

from __future__ import annotations

import json

from datetime import datetime, timezone
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
    check_agent_assurance,
    check_data_quality_assurance,
    check_decision_audit,
)

from src.dashboards.data_access import (
    DashboardRepository,
)

from src.validation.data_quality_monitoring import (
    check_data_staleness,
    check_duplicate_keys,
    check_future_dates,
    check_negative_values,
    check_required_columns,
    check_required_values,
    summarise_data_quality,
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


def evaluate_data_quality(
    *,
    repository: DashboardRepository,
    dashboard_settings: dict[str, Any],
) -> dict[str, int | str]:
    """Evaluate configured source-data quality rules."""

    monitoring_settings = (
        dashboard_settings.get(
            "data_quality_monitoring",
            {},
        )
    )

    if not bool(
        monitoring_settings.get(
            "enabled",
            True,
        )
    ):
        return {
            "status": "Passed",
            "total_findings": 0,
            "critical_findings": 0,
            "high_findings": 0,
            "medium_findings": 0,
        }

    datasets = {
        "inventory": (
            repository
            .load_data_quality_inventory()
        ),
        "issue_history": (
            repository
            .load_data_quality_issue_history()
        ),
        "repair_orders": (
            repository
            .load_data_quality_repair_orders()
        ),
    }

    findings = []

    required_fields = (
        monitoring_settings.get(
            "required_fields",
            {},
        )
    )

    duplicate_keys = (
        monitoring_settings.get(
            "duplicate_keys",
            {},
        )
    )

    non_negative_fields = (
        monitoring_settings.get(
            "non_negative_fields",
            {},
        )
    )

    date_fields = (
        monitoring_settings.get(
            "date_fields",
            {},
        )
    )

    for dataset_name, dataframe in datasets.items():
        required = required_fields.get(
            dataset_name,
            [],
        )

        findings.extend(
            check_required_columns(
                dataframe=dataframe,
                dataset=dataset_name,
                required_columns=required,
            )
        )

        findings.extend(
            check_required_values(
                dataframe=dataframe,
                dataset=dataset_name,
                required_columns=required,
            )
        )

        findings.extend(
            check_duplicate_keys(
                dataframe=dataframe,
                dataset=dataset_name,
                key_columns=duplicate_keys.get(
                    dataset_name,
                    [],
                ),
            )
        )

        findings.extend(
            check_negative_values(
                dataframe=dataframe,
                dataset=dataset_name,
                numeric_columns=(
                    non_negative_fields.get(
                        dataset_name,
                        [],
                    )
                ),
            )
        )

        findings.extend(
            check_future_dates(
                dataframe=dataframe,
                dataset=dataset_name,
                date_columns=date_fields.get(
                    dataset_name,
                    [],
                ),
            )
        )

    freshness_settings = (
        monitoring_settings.get(
            "freshness",
            {},
        )
    )

    for dataset_name, freshness_rule in (
        freshness_settings.items()
    ):
        if dataset_name not in datasets:
            continue

        date_field = freshness_rule.get(
            "date_field"
        )

        if not date_field:
            continue

        stale_after_days = int(
            freshness_rule.get(
                "stale_after_days",
                45,
            )
        )

        findings.extend(
            check_data_staleness(
                dataframe=datasets[
                    dataset_name
                ],
                dataset=dataset_name,
                date_column=date_field,
                reference_date=datetime.now(
                    timezone.utc
                ),
                stale_after_days=(
                    stale_after_days
                ),
            )
        )

    return summarise_data_quality(
        findings
    )


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

    audit_database_path = (
        PROJECT_ROOT
        / settings["paths"][
            "management_audit_database"
        ]
    )

    repository = DashboardRepository(
        database_path
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

    data_quality_summary = (
        evaluate_data_quality(
            repository=repository,
            dashboard_settings=settings[
                "dashboard"
            ],
        )
    )

    assurance_settings = (
        readiness_settings.get(
            "assurance",
            {},
        )
    )

    decision_audit_settings = (
        readiness_settings.get(
            "decision_audit",
            {},
        )
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

        check_data_quality_assurance(
            finding_count=int(
                data_quality_summary[
                    "total_findings"
                ]
            ),
            critical_count=int(
                data_quality_summary[
                    "critical_findings"
                ]
            ),
            high_count=int(
                data_quality_summary[
                    "high_findings"
                ]
            ),
            required=bool(
                assurance_settings.get(
                    "require_data_quality_passed",
                    True,
                )
            ),
        ),

        check_agent_assurance(
            database_path,
            required=bool(
                assurance_settings.get(
                    "require_agent_assurance",
                    True,
                )
            ),
        ),

        check_decision_audit(
            audit_database_path,
            required_table=str(
                decision_audit_settings.get(
                    "required_table",
                    "management_decision_audit",
                )
            ),
            required=bool(
                assurance_settings.get(
                    "require_decision_audit_available",
                    True,
                )
            ),
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

    if overall_status == "Passed":
        print(
            "CLASSIFICATION: READY FOR GOVERNED "
            "DECISION SUPPORT"
        )

        print(
            "Human approval remains required. "
            "Automatic purchasing and inventory "
            "write-back remain disabled."
        )

    else:
        print(
            "CLASSIFICATION: NOT READY FOR "
            "GOVERNED DECISION SUPPORT"
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
                "classification": (
                    "Ready for Governed Decision Support"
                    if overall_status == "Passed"
                    else (
                        "Not Ready for Governed"
                        "Decision Support"
                    )
                ),
                "human_approval_required": True,
                "automatic_purchasing_enabled": False,
                "inventory_writeback_enabled": False,
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