"""Tests for final production-readiness validation."""

from pathlib import Path

import duckdb

from src.validation.production_readiness import (
    ReadinessCheck,
    check_database_exists,
    check_required_tables,
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