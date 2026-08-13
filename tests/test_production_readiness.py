"""Tests for final production-readiness validation."""

from pathlib import Path

import duckdb

from src.validation.production_readiness import (
    ReadinessCheck,
    check_agent_assurance,
    check_data_quality_assurance,
    check_database_exists,
    check_decision_audit,
    check_governance,
    check_latest_pipeline,
    check_management_report,
    check_required_tables,
    check_scheduled_job_summary,
    check_scheduled_lock,
    determine_overall_status,
)


def test_database_exists(
    tmp_path: Path,
) -> None:
    """An existing database should pass."""

    database_path = (
        tmp_path
        / "test.duckdb"
    )

    with duckdb.connect(
        str(database_path)
    ):
        pass

    result = check_database_exists(
        database_path
    )

    assert result.status == "Passed"


def test_missing_database_fails(
    tmp_path: Path,
) -> None:
    """A missing database should fail."""

    result = check_database_exists(
        tmp_path
        / "missing.duckdb"
    )

    assert result.status == "Failed"


def test_required_table_validation(
    tmp_path: Path,
) -> None:
    """Required populated tables should pass."""

    database_path = (
        tmp_path
        / "test.duckdb"
    )

    with duckdb.connect(
        str(database_path)
    ) as connection:
        connection.execute(
            """
            CREATE TABLE inventory (
                part_number VARCHAR
            )
            """
        )

        connection.execute(
            """
            INSERT INTO inventory
            VALUES ('PN-001')
            """
        )

    results = check_required_tables(
        database_path,
        [
            "inventory",
        ],
    )

    assert len(results) == 1
    assert results[0].status == "Passed"


def test_missing_required_table_fails(
    tmp_path: Path,
) -> None:
    """A missing required table should fail."""

    database_path = (
        tmp_path
        / "test.duckdb"
    )

    with duckdb.connect(
        str(database_path)
    ):
        pass

    results = check_required_tables(
        database_path,
        [
            "inventory",
        ],
    )

    assert results[0].status == "Failed"


def test_overall_status_passes() -> None:
    """All passed checks should produce Passed."""

    checks = [
        ReadinessCheck(
            "A",
            "Passed",
            "OK",
        ),
        ReadinessCheck(
            "B",
            "Passed",
            "OK",
        ),
    ]

    assert (
        determine_overall_status(
            checks
        )
        == "Passed"
    )


def test_overall_status_fails() -> None:
    """One failed check should fail readiness."""

    checks = [
        ReadinessCheck(
            "A",
            "Passed",
            "OK",
        ),
        ReadinessCheck(
            "B",
            "Failed",
            "Problem",
        ),
    ]

    assert (
        determine_overall_status(
            checks
        )
        == "Failed"
    )


def test_data_quality_assurance_passes() -> None:
    """Data quality passes without Critical or High findings."""

    result = check_data_quality_assurance(
        finding_count=2,
        critical_count=0,
        high_count=0,
    )

    assert result.status == "Passed"


def test_data_quality_assurance_fails_for_high() -> None:
    """High-severity data-quality findings block readiness."""

    result = check_data_quality_assurance(
        finding_count=2,
        critical_count=0,
        high_count=1,
    )

    assert result.status == "Failed"


def test_agent_assurance_passes(
    tmp_path: Path,
) -> None:
    """Fully assured agent evidence passes readiness."""

    database_path = (
        tmp_path
        / "agent_assurance.duckdb"
    )

    with duckdb.connect(
        str(database_path)
    ) as connection:
        connection.execute(
            """
            CREATE TABLE agent_assurance_findings (
                assurance_status VARCHAR,
                evidence_complete BOOLEAN,
                governance_compliant BOOLEAN,
                approved_for_management_display BOOLEAN
            )
            """
        )

        connection.execute(
            """
            INSERT INTO agent_assurance_findings
            VALUES (
                'Passed',
                TRUE,
                TRUE,
                TRUE
            )
            """
        )

    result = check_agent_assurance(
        database_path
    )

    assert result.status == "Passed"


def test_agent_assurance_fails_for_unapproved_record(
    tmp_path: Path,
) -> None:
    """Unapproved agent evidence blocks readiness."""

    database_path = (
        tmp_path
        / "agent_assurance.duckdb"
    )

    with duckdb.connect(
        str(database_path)
    ) as connection:
        connection.execute(
            """
            CREATE TABLE agent_assurance_findings (
                assurance_status VARCHAR,
                evidence_complete BOOLEAN,
                governance_compliant BOOLEAN,
                approved_for_management_display BOOLEAN
            )
            """
        )

        connection.execute(
            """
            INSERT INTO agent_assurance_findings
            VALUES (
                'Failed',
                FALSE,
                TRUE,
                FALSE
            )
            """
        )

    result = check_agent_assurance(
        database_path
    )

    assert result.status == "Failed"


def test_decision_audit_passes(
    tmp_path: Path,
) -> None:
    """Available decision-audit store passes readiness."""

    database_path = (
        tmp_path
        / "management_audit.duckdb"
    )

    with duckdb.connect(
        str(database_path)
    ) as connection:
        connection.execute(
            """
            CREATE TABLE management_decision_audit (
                audit_id VARCHAR
            )
            """
        )

    result = check_decision_audit(
        database_path,
        required_table=(
            "management_decision_audit"
        ),
    )

    assert result.status == "Passed"


def test_decision_audit_fails_when_missing(
    tmp_path: Path,
) -> None:
    """Missing decision-audit database blocks readiness."""

    result = check_decision_audit(
        tmp_path
        / "missing.duckdb",
        required_table=(
            "management_decision_audit"
        ),
    )

    assert result.status == "Failed"