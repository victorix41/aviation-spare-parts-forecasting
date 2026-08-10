"""Tests for dashboard data access and formatting."""

from pathlib import Path
from datetime import UTC, datetime, timedelta

import duckdb
import pandas as pd
import pytest

from src.dashboards.dashboard_utils import (
    determine_pipeline_freshness,
    determine_readiness_status,
    format_currency,
    format_quantity,
    prepare_risk_summary,
)
from src.dashboards.data_access import (
    DashboardDataError,
    DashboardRepository,
)
from datetime import UTC, datetime, timedelta


def create_dashboard_database(
    database_path: Path,
) -> None:
    """Create a minimal dashboard test database."""

    optimisation = pd.DataFrame(
        {
            "part_number": [
                "PN-001",
                "PN-002",
            ],
            "stockout_risk": [
                "Critical",
                "Low",
            ],
            "inventory_value_usd": [
                100.0,
                500.0,
            ],
            "procurement_value_usd": [
                1000.0,
                0.0,
            ],
            "recommended_order_quantity": [
                10.0,
                0.0,
            ],
            "current_balance": [
                0.0,
                5.0,
            ],
            "human_approval_required": [
                True,
                True,
            ],
        }
    )

    procurement = pd.DataFrame(
        {
            "procurement_priority": [1],
            "part_number": ["PN-001"],
            "description": ["Bearing"],
            "engineering_criticality": ["High"],
            "stockout_risk": ["Critical"],
            "forecast_confidence": ["Low"],
            "current_balance": [0.0],
            "reorder_point": [5.0],
            "recommended_order_quantity": [10.0],
            "procurement_value_usd": [1000.0],
            "average_lead_time_days": [45.0],
            "recommendation_status": [
                "Order review required"
            ],
        }
    )

    recommendations = pd.DataFrame(
        {
            "recommendation_id": ["REC-001"],
            "priority": ["Critical"],
            "agent_name": ["Executive Agent"],
            "target_role": ["Accountable Manager"],
            "part_number": [None],
            "title": ["Critical stock exposure"],
            "recommendation": ["Review exposure."],
            "rationale": ["One critical part."],
            "forecast_confidence": [None],
            "status": ["Pending review"],
            "assurance_status": ["Passed"],
            "approved_for_management_display": [True],
        }
    )

    selected_models = pd.DataFrame(
        {
            "selected_model": ["croston_sba"],
            "selection_score": [0.5],
            "bias": [0.1],
        }
    )

    with duckdb.connect(
        str(database_path)
    ) as connection:
        connection.register(
            "optimisation_frame",
            optimisation,
        )
        connection.execute(
            """
            CREATE TABLE inventory_optimisation_results
            AS SELECT * FROM optimisation_frame
            """
        )
        connection.unregister(
            "optimisation_frame"
        )

        connection.register(
            "procurement_frame",
            procurement,
        )
        connection.execute(
            """
            CREATE TABLE procurement_recommendations
            AS SELECT * FROM procurement_frame
            """
        )
        connection.unregister(
            "procurement_frame"
        )

        connection.register(
            "recommendation_frame",
            recommendations,
        )
        connection.execute(
            """
            CREATE TABLE agent_recommendations
            AS SELECT * FROM recommendation_frame
            """
        )
        connection.unregister(
            "recommendation_frame"
        )

        connection.register(
            "selected_model_frame",
            selected_models,
        )
        connection.execute(
            """
            CREATE TABLE selected_forecast_models
            AS SELECT * FROM selected_model_frame
            """
        )
        connection.unregister(
            "selected_model_frame"
        )


def test_dashboard_repository_requires_database(
    tmp_path: Path,
) -> None:
    """A missing database should raise a readable error."""

    repository = DashboardRepository(
        tmp_path / "missing.duckdb"
    )

    with pytest.raises(
        DashboardDataError,
        match="not found",
    ):
        repository.load_executive_kpis()


def test_dashboard_repository_loads_kpis(
    tmp_path: Path,
) -> None:
    """Executive KPIs should be calculated correctly."""

    database_path = (
        tmp_path
        / "dashboard.duckdb"
    )

    create_dashboard_database(
        database_path
    )

    repository = DashboardRepository(
        database_path
    )

    kpis = repository.load_executive_kpis()

    assert kpis["forecast_parts"] == 2
    assert kpis["critical_parts"] == 1
    assert kpis["high_risk_parts"] == 0
    assert kpis["procurement_recommendations"] == 1
    assert kpis["approved_advisories"] == 1
    assert kpis["procurement_value_usd"] == 1000.0


def test_dashboard_repository_rejects_write_query(
    tmp_path: Path,
) -> None:
    """Dashboard queries must remain read-only."""

    database_path = (
        tmp_path
        / "dashboard.duckdb"
    )

    create_dashboard_database(
        database_path
    )

    repository = DashboardRepository(
        database_path
    )

    with pytest.raises(
        DashboardDataError,
        match="read-only",
    ):
        repository.query(
            "DELETE FROM procurement_recommendations"
        )


def test_formatting_helpers() -> None:
    """Dashboard number formatting should be consistent."""

    assert format_currency(
        1234.5
    ) == "USD 1,234.50"

    assert format_quantity(
        1234.5
    ) == "1,234"


def test_risk_ordering() -> None:
    """Risk summaries should follow management order."""

    dataframe = pd.DataFrame(
        {
            "stockout_risk": [
                "Low",
                "Critical",
                "Medium",
                "High",
            ],
            "part_count": [
                10,
                1,
                2,
                5,
            ],
        }
    )

    result = prepare_risk_summary(
        dataframe,
        [
            "Critical",
            "High",
            "Medium",
            "Low",
        ],
    )

    assert result[
        "stockout_risk"
    ].astype(str).tolist() == [
        "Critical",
        "High",
        "Medium",
        "Low",
    ]

def test_readiness_status_is_red() -> None:
    """Material portfolio risk should produce red readiness."""

    status, icon, _ = determine_readiness_status(
        critical_parts=6,
        high_risk_parts=35,
        procurement_exposure_usd=1385368.93,
        settings={
            "critical_parts_red_threshold": 5,
            "critical_parts_amber_threshold": 1,
            "high_risk_parts_red_threshold": 30,
            "high_risk_parts_amber_threshold": 10,
            "procurement_exposure_red_usd": 1000000,
            "procurement_exposure_amber_usd": 500000,
        },
    )

    assert status == "Critical Attention"
    assert icon == "🔴"


def test_readiness_status_is_stable() -> None:
    """Low portfolio exposure should produce green readiness."""

    status, icon, _ = determine_readiness_status(
        critical_parts=0,
        high_risk_parts=2,
        procurement_exposure_usd=100000,
        settings={
            "critical_parts_red_threshold": 5,
            "critical_parts_amber_threshold": 1,
            "high_risk_parts_red_threshold": 30,
            "high_risk_parts_amber_threshold": 10,
            "procurement_exposure_red_usd": 1000000,
            "procurement_exposure_amber_usd": 500000,
        },
    )

    assert status == "Stable"
    assert icon == "🟢"

def test_pipeline_freshness_is_current() -> None:
    """A recent pipeline completion should be current."""

    completed_at = (
        datetime.now(UTC)
        - timedelta(hours=2)
    )

    status, age_hours = determine_pipeline_freshness(
        completed_at=completed_at,
        stale_after_hours=24,
    )

    assert status == "Current"
    assert 1.0 < age_hours < 3.0


def test_pipeline_freshness_is_stale() -> None:
    """An old pipeline completion should be stale."""

    completed_at = (
        datetime.now(UTC)
        - timedelta(hours=30)
    )

    status, age_hours = determine_pipeline_freshness(
        completed_at=completed_at,
        stale_after_hours=24,
    )

    assert status == "Stale"
    assert age_hours > 24

def test_management_drilldown_parts(
    tmp_path: Path,
) -> None:
    """Management drill-down should return optimisation records."""

    database_path = (
        tmp_path
        / "dashboard_test.duckdb"
    )

    with duckdb.connect(
        str(database_path)
    ) as connection:
        connection.execute(
            """
            CREATE TABLE inventory_optimisation_results (
                part_number VARCHAR,
                description VARCHAR,
                engineering_criticality VARCHAR,
                stockout_risk VARCHAR,
                procurement_priority INTEGER,
                forecast_confidence VARCHAR,
                selected_forecast_model VARCHAR,
                current_balance DOUBLE,
                average_monthly_demand DOUBLE,
                forecast_3m DOUBLE,
                forecast_6m DOUBLE,
                forecast_12m DOUBLE,
                safety_stock DOUBLE,
                reorder_point DOUBLE,
                months_of_stock_cover DOUBLE,
                estimated_stockout_months DOUBLE,
                recommended_order_quantity DOUBLE,
                procurement_value_usd DOUBLE,
                average_lead_time_days DOUBLE,
                recommendation_status VARCHAR,
                recommendation_reason VARCHAR
            )
            """
        )

        connection.execute(
            """
            INSERT INTO inventory_optimisation_results
            VALUES (
                'PN-001',
                'Test Part',
                'Critical',
                'Critical',
                1,
                'Medium',
                'croston_sba',
                2,
                3.5,
                10,
                20,
                40,
                5,
                8,
                0.57,
                0.57,
                25,
                12500.00,
                45,
                'Order review required',
                'Critical stock risk.'
            )
            """
        )

    repository = DashboardRepository(
        database_path
    )

    result = (
        repository
        .load_management_drilldown_parts(
            stockout_risk="Critical",
            limit=10,
        )
    )

    assert isinstance(
        result,
        pd.DataFrame,
    )

    assert len(result) == 1

    assert (
        result.iloc[0][
            "part_number"
        ]
        == "PN-001"
    )

    assert (
        result.iloc[0][
            "stockout_risk"
        ]
        == "Critical"
    )