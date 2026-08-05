"""Run the Phase 3.5 agentic advisory engine."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import yaml

from src.agents.advisory_orchestrator import (
    run_advisory_orchestration,
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
            "Settings must be a YAML mapping."
        )

    return settings


def load_source_tables(
    database_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load optimisation and procurement tables."""

    if not database_path.is_file():
        raise FileNotFoundError(
            "DuckDB database was not found."
        )

    with duckdb.connect(
        str(database_path),
        read_only=True,
    ) as connection:
        optimisation_data = connection.execute(
            """
            SELECT *
            FROM inventory_optimisation_results
            """
        ).fetchdf()

        procurement_data = connection.execute(
            """
            SELECT *
            FROM procurement_recommendations
            """
        ).fetchdf()

    return optimisation_data, procurement_data


def write_dataframe(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    dataframe: pd.DataFrame,
) -> None:
    """Write a DataFrame to DuckDB."""

    temporary_name = (
        f"temporary_{table_name}"
    )

    connection.register(
        temporary_name,
        dataframe,
    )

    try:
        connection.execute(
            f"""
            CREATE OR REPLACE TABLE
            "{table_name}"
            AS
            SELECT *
            FROM "{temporary_name}"
            """
        )
    finally:
        connection.unregister(
            temporary_name
        )


def main() -> None:
    """Run Phase 3.5."""

    settings = load_settings()

    database_path = (
        PROJECT_ROOT
        / settings["paths"]["database"]
    )

    reports_directory = (
        PROJECT_ROOT
        / settings["paths"]["reports"]
    )

    exports_directory = (
        PROJECT_ROOT
        / settings["paths"]["exports"]
    )

    agent_settings = settings[
        "agentic_ai"
    ]

    (
        optimisation_data,
        procurement_data,
    ) = load_source_tables(
        database_path
    )

    orchestration = run_advisory_orchestration(
        optimisation_data=optimisation_data,
        procurement_data=procurement_data,
        settings=agent_settings,
    )

    assurance_by_id = {
        finding.recommendation_id: finding
        for finding
        in orchestration.assurance_findings
    }

    recommendation_rows: list[
        dict[str, Any]
    ] = []

    for recommendation in (
        orchestration.recommendations
    ):
        record = recommendation.to_dict()

        record["evidence"] = json.dumps(
            record["evidence"],
            default=str,
            sort_keys=True,
        )

        assurance = assurance_by_id[
            recommendation.recommendation_id
        ]

        record[
            "assurance_status"
        ] = assurance.assurance_status

        record[
            "approved_for_management_display"
        ] = (
            assurance
            .approved_for_management_display
        )

        recommendation_rows.append(
            record
        )

    assurance_rows = [
        finding.to_dict()
        for finding
        in orchestration.assurance_findings
    ]

    recommendation_frame = pd.DataFrame(
        recommendation_rows
    )

    assurance_frame = pd.DataFrame(
        assurance_rows
    )

    approved_frame = (
        recommendation_frame.loc[
            recommendation_frame[
                "approved_for_management_display"
            ]
        ]
        .copy()
        .reset_index(drop=True)
    )

    role_summary = (
        approved_frame.groupby(
            [
                "target_role",
                "priority",
            ],
            as_index=False,
        )
        .agg(
            recommendation_count=(
                "recommendation_id",
                "count",
            )
        )
    )

    output_tables = agent_settings[
        "output_tables"
    ]

    table_frames = {
        output_tables[
            "agent_recommendations"
        ]: approved_frame,
        output_tables[
            "role_advisory_summary"
        ]: role_summary,
        output_tables[
            "assurance_findings"
        ]: assurance_frame,
    }

    with duckdb.connect(
        str(database_path)
    ) as connection:
        for table_name, dataframe in (
            table_frames.items()
        ):
            write_dataframe(
                connection,
                table_name,
                dataframe,
            )

    exports_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for table_name, dataframe in (
        table_frames.items()
    ):
        dataframe.to_parquet(
            exports_directory
            / f"{table_name}.parquet",
            index=False,
        )

    reports_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    agent_counts = Counter(
        approved_frame[
            "agent_name"
        ].tolist()
        if not approved_frame.empty
        else []
    )

    role_counts = Counter(
        approved_frame[
            "target_role"
        ].tolist()
        if not approved_frame.empty
        else []
    )

    priority_counts = Counter(
        approved_frame[
            "priority"
        ].tolist()
        if not approved_frame.empty
        else []
    )

    passed_assurance = int(
        assurance_frame[
            "approved_for_management_display"
        ].sum()
    )

    summary = {
        "recommendations_generated": int(
            len(recommendation_frame)
        ),
        "recommendations_approved": int(
            len(approved_frame)
        ),
        "recommendations_rejected": int(
            len(recommendation_frame)
            - len(approved_frame)
        ),
        "assurance_passed": passed_assurance,
        "agent_counts": dict(
            agent_counts
        ),
        "role_counts": dict(
            role_counts
        ),
        "priority_counts": dict(
            priority_counts
        ),
        "automatic_actions_allowed": False,
        "human_approval_required": True,
        "success": (
            len(approved_frame)
            == passed_assurance
        ),
    }

    with (
        reports_directory
        / "agentic_advisory_summary.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            indent=2,
        )

    separator = "=" * 72

    print(separator)
    print(
        "AVIATION SPARE PARTS — "
        "PHASE 3.5 AGENTIC AI ADVISORY"
    )
    print(separator)
    print(
        f"Recommendations generated: "
        f"{summary['recommendations_generated']:,}"
    )
    print(
        f"Recommendations approved: "
        f"{summary['recommendations_approved']:,}"
    )
    print(
        f"Recommendations rejected: "
        f"{summary['recommendations_rejected']:,}"
    )
    print(
        f"Agent recommendations: "
        f"{summary['agent_counts']}"
    )
    print(
        f"Role recommendations: "
        f"{summary['role_counts']}"
    )
    print(
        f"Priority distribution: "
        f"{summary['priority_counts']}"
    )
    print(
        "Automatic actions allowed: "
        f"{summary['automatic_actions_allowed']}"
    )
    print(
        "Human approval required: "
        f"{summary['human_approval_required']}"
    )
    print(
        f"Advisory engine passed: "
        f"{summary['success']}"
    )
    print(separator)


if __name__ == "__main__":
    main()