"""Read-only DuckDB access for management dashboards."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from datetime import datetime

import duckdb
import pandas as pd


class DashboardDataError(RuntimeError):
    """Raised when dashboard data cannot be retrieved."""


class DashboardRepository:
    """Provide read-only access to validated analytics tables."""

    def __init__(self, database_path: Path) -> None:
        """Initialise the dashboard repository."""

        self.database_path = Path(database_path)

    def validate_database(self) -> None:
        """Confirm that the project database exists."""

        if not self.database_path.is_file():
            raise DashboardDataError(
                "DuckDB database was not found. Run the ingestion, "
                "analytics, forecasting, optimisation and advisory "
                "pipelines before opening the dashboard."
            )

    @contextmanager
    def connect(
        self,
    ) -> Iterator[duckdb.DuckDBPyConnection]:
        """Open and safely close a read-only DuckDB connection."""

        self.validate_database()

        connection: duckdb.DuckDBPyConnection | None = None

        try:
            connection = duckdb.connect(
                str(self.database_path),
                read_only=True,
            )
            yield connection
        except Exception as exc:
            raise DashboardDataError(
                f"Dashboard database query failed: {exc}"
            ) from exc
        finally:
            if connection is not None:
                connection.close()

    def table_exists(
        self,
        table_name: str,
    ) -> bool:
        """Return whether a required table exists."""

        with self.connect() as connection:
            result = connection.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'main'
                  AND table_name = ?
                """,
                [table_name],
            ).fetchone()

        return bool(result and result[0] > 0)

    def require_tables(
        self,
        table_names: list[str],
    ) -> None:
        """Ensure all dashboard source tables exist."""

        missing = [
            table_name
            for table_name in table_names
            if not self.table_exists(table_name)
        ]

        if missing:
            raise DashboardDataError(
                "Required dashboard tables are missing: "
                + ", ".join(sorted(missing))
            )

    def query(
        self,
        sql: str,
        parameters: list[object] | None = None,
    ) -> pd.DataFrame:
        """Execute a read-only query and return a DataFrame."""

        stripped = sql.strip().lower()

        if not stripped.startswith(
            (
                "select",
                "with",
                "show",
                "describe",
            )
        ):
            raise DashboardDataError(
                "DashboardRepository only permits read-only queries."
            )

        with self.connect() as connection:
            return connection.execute(
                sql,
                parameters or [],
            ).fetchdf()

    def load_executive_kpis(self) -> dict[str, float | int]:
        """Load executive-level KPI values."""

        self.require_tables(
            [
                "inventory_optimisation_results",
                "procurement_recommendations",
                "agent_recommendations",
            ]
        )

        query = """
            SELECT
                COUNT(DISTINCT part_number)
                    AS forecast_parts,
                SUM(inventory_value_usd)
                    AS inventory_value_usd,
                SUM(procurement_value_usd)
                    AS procurement_value_usd,
                SUM(recommended_order_quantity)
                    AS recommended_order_quantity,
                SUM(
                    CASE
                        WHEN stockout_risk = 'Critical'
                        THEN 1
                        ELSE 0
                    END
                ) AS critical_parts,
                SUM(
                    CASE
                        WHEN stockout_risk = 'High'
                        THEN 1
                        ELSE 0
                    END
                ) AS high_risk_parts,
                SUM(
                    CASE
                        WHEN human_approval_required
                        THEN 1
                        ELSE 0
                    END
                ) AS human_approval_records
            FROM inventory_optimisation_results
        """

        result = self.query(query)

        if result.empty:
            return {
                "forecast_parts": 0,
                "inventory_value_usd": 0.0,
                "procurement_value_usd": 0.0,
                "recommended_order_quantity": 0.0,
                "critical_parts": 0,
                "high_risk_parts": 0,
                "human_approval_records": 0,
                "procurement_recommendations": 0,
                "approved_advisories": 0,
            }

        row = result.iloc[0]

        procurement_count = int(
            self.query(
                """
                SELECT COUNT(*) AS record_count
                FROM procurement_recommendations
                """
            ).iloc[0]["record_count"]
        )

        advisory_count = int(
            self.query(
                """
                SELECT COUNT(*) AS record_count
                FROM agent_recommendations
                WHERE approved_for_management_display = TRUE
                """
            ).iloc[0]["record_count"]
        )

        return {
            "forecast_parts": int(row["forecast_parts"] or 0),
            "inventory_value_usd": float(
                row["inventory_value_usd"] or 0.0
            ),
            "procurement_value_usd": float(
                row["procurement_value_usd"] or 0.0
            ),
            "recommended_order_quantity": float(
                row["recommended_order_quantity"] or 0.0
            ),
            "critical_parts": int(row["critical_parts"] or 0),
            "high_risk_parts": int(row["high_risk_parts"] or 0),
            "human_approval_records": int(
                row["human_approval_records"] or 0
            ),
            "procurement_recommendations": procurement_count,
            "approved_advisories": advisory_count,
        }

    def load_risk_summary(self) -> pd.DataFrame:
        """Load inventory-risk totals."""

        return self.query(
            """
            SELECT
                stockout_risk,
                COUNT(*) AS part_count,
                SUM(current_balance) AS current_balance,
                SUM(recommended_order_quantity)
                    AS recommended_order_quantity,
                SUM(inventory_value_usd)
                    AS inventory_value_usd,
                SUM(procurement_value_usd)
                    AS procurement_value_usd
            FROM inventory_optimisation_results
            GROUP BY stockout_risk
            """
        )

    def load_model_summary(self) -> pd.DataFrame:
        """Load selected forecasting-model distribution."""

        return self.query(
            """
            SELECT
                selected_model,
                COUNT(*) AS part_count,
                AVG(selection_score) AS average_selection_score,
                AVG(ABS(bias)) AS average_absolute_bias
            FROM selected_forecast_models
            GROUP BY selected_model
            ORDER BY part_count DESC, selected_model
            """
        )

    def load_priority_recommendations(
        self,
        limit: int = 20,
    ) -> pd.DataFrame:
        """Load highest-priority procurement recommendations."""

        return self.query(
            """
            SELECT
                procurement_priority,
                part_number,
                description,
                engineering_criticality,
                stockout_risk,
                forecast_confidence,
                current_balance,
                reorder_point,
                recommended_order_quantity,
                procurement_value_usd,
                average_lead_time_days,
                recommendation_status
            FROM procurement_recommendations
            ORDER BY
                procurement_priority,
                procurement_value_usd DESC
            LIMIT ?
            """,
            [int(limit)],
        )

    def load_role_recommendations(
        self,
        target_role: str,
        limit: int = 50,
    ) -> pd.DataFrame:
        """Load assured recommendations for one management role."""

        return self.query(
            """
            SELECT
                recommendation_id,
                priority,
                agent_name,
                target_role,
                part_number,
                title,
                recommendation,
                rationale,
                forecast_confidence,
                status,
                assurance_status
            FROM agent_recommendations
            WHERE target_role = ?
              AND approved_for_management_display = TRUE
            ORDER BY
                CASE priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    ELSE 4
                END,
                part_number
            LIMIT ?
            """,
            [
                target_role,
                int(limit),
            ],
        )

    def load_data_status(self) -> pd.DataFrame:
        """Return key source-table row counts."""

        table_names = [
            "inventory",
            "issue_history",
            "repair_orders",
            "monthly_demand",
            "demand_metrics",
            "forecast_backtest_results",
            "selected_forecast_models",
            "final_part_forecasts",
            "inventory_optimisation_results",
            "procurement_recommendations",
            "agent_recommendations",
            "agent_assurance_findings",
        ]

        rows: list[dict[str, object]] = []

        for table_name in table_names:
            if not self.table_exists(table_name):
                rows.append(
                    {
                        "table_name": table_name,
                        "row_count": 0,
                        "status": "Missing",
                    }
                )
                continue

            result = self.query(
                f'SELECT COUNT(*) AS row_count FROM "{table_name}"'
            )

            rows.append(
                {
                    "table_name": table_name,
                    "row_count": int(
                        result.iloc[0]["row_count"]
                    ),
                    "status": "Available",
                }
            )

        return pd.DataFrame(rows)

    def load_database_refresh_time(
        self,
    ) -> datetime:
        """Return the DuckDB file's latest modification time."""

        self.validate_database()

        timestamp = self.database_path.stat().st_mtime

        return datetime.fromtimestamp(timestamp)

    def load_forecast_confidence_summary(
        self,   
    ) -> pd.DataFrame:
        """Load forecast-confidence distribution."""

        self.require_tables(
            [
                "final_part_forecasts",
            ]
        )

        return self.query(
            """
            SELECT
                forecast_confidence,
                COUNT(*) AS part_count
            FROM final_part_forecasts
            GROUP BY forecast_confidence
            ORDER BY
                CASE forecast_confidence
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Low' THEN 3
                    ELSE 4
                END
            """
    )

    def load_advisory_priority_summary(
        self,
    ) -> pd.DataFrame:
        """Load assured advisory counts by priority."""

        self.require_tables(
            [
             "agent_recommendations",
            ]
        )

        return self.query(
            """
            SELECT
                priority,
                COUNT(*) AS recommendation_count
            FROM agent_recommendations
            WHERE approved_for_management_display = TRUE
            GROUP BY priority
            ORDER BY
                CASE priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END
            """
        )

    def load_part_drilldown_list(
        self,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Load parts available for executive drill-down."""

        return self.query(
            """
            SELECT
                part_number,
                description,
                stockout_risk,
                procurement_priority,
                procurement_value_usd
            FROM inventory_optimisation_results
            ORDER BY
                procurement_priority,
                procurement_value_usd DESC,
                part_number
            LIMIT ?
            """,
            [
                int(limit),
            ],
        )

    def load_part_drilldown(
        self,
        part_number: str,
    ) -> pd.DataFrame:
        """Load a consolidated management view for one part."""

        return self.query(
            """
            SELECT
                o.part_number,
                o.description,
                o.engineering_criticality,
                o.demand_pattern,
                o.selected_forecast_model,
                o.forecast_confidence,
                o.current_balance,
                o.average_monthly_demand,
                o.forecast_3m,
                o.forecast_6m,
                o.forecast_12m,
                o.average_lead_time_days,
                o.safety_stock,
                o.reorder_point,
                o.months_of_stock_cover,
                o.stockout_risk,
                o.recommended_order_quantity,
                o.procurement_value_usd,
                o.recommendation_status,
                o.recommendation_reason
            FROM inventory_optimisation_results o
            WHERE o.part_number = ?
            """,
            [
                part_number,
            ],
        )

    def load_part_advisories(
        self,
        part_number: str,
    ) -> pd.DataFrame:
        """Load assured agent recommendations for one part."""

        return self.query(
            """
            SELECT
                priority,
                target_role,
                agent_name,
                title,
                recommendation,
                rationale,
                forecast_confidence,
                status
            FROM agent_recommendations
            WHERE part_number = ?
            AND approved_for_management_display = TRUE
            ORDER BY
                CASE priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    ELSE 4
                END,
                target_role
            """,
            [
                part_number,
            ],
        )

    def load_procurement_kpis(self) -> dict[str, float | int]:
        """Load Procurement Manager KPI values."""

        self.require_tables(
            [
                "inventory_optimisation_results",
                "procurement_recommendations",
            ]
        )

        result = self.query(
            """
            SELECT
                COUNT(*) AS recommendation_count,
                SUM(recommended_order_quantity)
                    AS recommended_order_quantity,
                SUM(procurement_value_usd)
                    AS procurement_value_usd,
                SUM(
                    CASE
                        WHEN procurement_priority = 1
                        THEN 1
                        ELSE 0
                    END
                ) AS critical_priority_count,
                SUM(
                    CASE
                        WHEN average_lead_time_days >= 90
                        THEN 1
                        ELSE 0
                    END
                ) AS long_lead_time_count,
                SUM(
                    CASE
                        WHEN procurement_value_usd >= 50000
                        THEN 1
                        ELSE 0
                    END
                ) AS high_value_count
            FROM procurement_recommendations
            """
        )

        row = result.iloc[0]

        return {
            "recommendation_count": int(
                row["recommendation_count"] or 0
            ),
            "recommended_order_quantity": float(
                row["recommended_order_quantity"] or 0.0
            ),
            "procurement_value_usd": float(
                row["procurement_value_usd"] or 0.0
            ),
            "critical_priority_count": int(
                row["critical_priority_count"] or 0
            ),
            "long_lead_time_count": int(
                row["long_lead_time_count"] or 0
            ),
            "high_value_count": int(
                row["high_value_count"] or 0
            ),
        }

    def load_procurement_dashboard_data(
        self,
    ) -> pd.DataFrame:
        """Load all Procurement Manager review records."""

        return self.query(
            """
            SELECT
                procurement_priority,
                part_number,
                description,
                engineering_criticality,
                stockout_risk,
                forecast_confidence,
                selected_forecast_model,
                current_balance,
                safety_stock,
                reorder_point,
                recommended_order_quantity,
                unit_price_usd,
                procurement_value_usd,
                average_lead_time_days,
                months_of_stock_cover,
                recommendation_status,
                recommendation_reason
            FROM procurement_recommendations
            ORDER BY
                procurement_priority,
                procurement_value_usd DESC
            """
        )
          

    def load_finance_kpis(self) -> dict[str, float | int]:
        """Load Finance Manager KPI values."""

        result = self.query(
            """
            SELECT
                SUM(inventory_value_usd)
                    AS inventory_value_usd,
                SUM(procurement_value_usd)
                    AS procurement_value_usd,
                SUM(recommended_order_quantity)
                    AS recommended_order_quantity,
                SUM(
                    CASE
                        WHEN procurement_value_usd >= 100000
                        THEN 1
                        ELSE 0
                    END
                ) AS six_figure_orders,
                SUM(
                    CASE
                        WHEN forecast_confidence = 'Low'
                        AND procurement_value_usd > 0
                        THEN procurement_value_usd
                        ELSE 0
                    END
                ) AS low_confidence_exposure_usd
            FROM inventory_optimisation_results
            """
        )

        row = result.iloc[0]

        return {
            "inventory_value_usd": float(
                row["inventory_value_usd"] or 0.0
            ),
            "procurement_value_usd": float(
                row["procurement_value_usd"] or 0.0
            ),
            "recommended_order_quantity": float(
                row["recommended_order_quantity"] or 0.0
            ),
            "six_figure_orders": int(
                row["six_figure_orders"] or 0
            ),
            "low_confidence_exposure_usd": float(
                row["low_confidence_exposure_usd"] or 0.0
            ),
        }

    def load_finance_exposure(self) -> pd.DataFrame:
        """Load part-level Finance Manager exposure."""

        return self.query(
            """
            SELECT
                part_number,
                description,
                stockout_risk,
                forecast_confidence,
                selected_forecast_model,
                current_balance,
                inventory_value_usd,
                recommended_order_quantity,
                procurement_value_usd,
                forecast_12m,
                engineering_criticality
            FROM inventory_optimisation_results
            WHERE procurement_value_usd > 0
            ORDER BY procurement_value_usd DESC
            """
        )

    def load_engineering_kpis(self) -> dict[str, int]:
        """Load Engineering Manager KPI values."""

        result = self.query(
            """
            SELECT
                SUM(
                    CASE
                        WHEN engineering_criticality = 'Critical'
                        THEN 1
                        ELSE 0
                    END
                ) AS critical_parts,
                SUM(
                    CASE
                        WHEN engineering_criticality = 'High'
                        THEN 1
                        ELSE 0
                    END
                ) AS high_criticality_parts,
                SUM(
                    CASE
                        WHEN engineering_criticality
                            IN ('Critical', 'High')
                        AND recommended_order_quantity > 0
                        THEN 1
                        ELSE 0
                    END
                ) AS engineering_reviews,
                SUM(
                    CASE
                        WHEN forecast_confidence = 'Low'
                        AND engineering_criticality
                            IN ('Critical', 'High')
                        THEN 1
                        ELSE 0
                    END
                ) AS low_confidence_critical_parts
            FROM inventory_optimisation_results
            """
        )

        row = result.iloc[0]

        return {
            "critical_parts": int(
                row["critical_parts"] or 0
            ),
            "high_criticality_parts": int(
                row["high_criticality_parts"] or 0
            ),
            "engineering_reviews": int(
                row["engineering_reviews"] or 0
            ),
            "low_confidence_critical_parts": int(
                row["low_confidence_critical_parts"] or 0
            ),
        }

    def load_engineering_review_data(
        self,
    ) -> pd.DataFrame:
        """Load Engineering Manager review records."""

        return self.query(
            """
            SELECT
                part_number,
                description,
                engineering_criticality,
                demand_pattern,
                selected_forecast_model,
                forecast_confidence,
                current_balance,
                reorder_point,
                recommended_order_quantity,
                procurement_value_usd,
                stockout_risk,
                recommendation_reason
            FROM inventory_optimisation_results
            WHERE engineering_criticality
                IN ('Critical', 'High')
            ORDER BY
                CASE engineering_criticality
                    WHEN 'Critical' THEN 1
                    ELSE 2
                END,
                procurement_priority,
                procurement_value_usd DESC
            """
        )

    def load_operations_kpis(self) -> dict[str, int | float]:
        """Load Operations Manager KPI values."""

        result = self.query(
            """
            SELECT
                SUM(
                    CASE
                        WHEN stockout_risk = 'Critical'
                        THEN 1
                        ELSE 0
                    END
                ) AS critical_stockouts,
                SUM(
                    CASE
                        WHEN stockout_risk = 'High'
                        THEN 1
                        ELSE 0
                    END
                ) AS high_stockouts,
                SUM(
                    CASE
                        WHEN estimated_stockout_months <= 0.5
                        THEN 1
                        ELSE 0
                    END
                ) AS immediate_exposure,
                SUM(
                    CASE
                        WHEN estimated_stockout_months > 0.5
                        AND estimated_stockout_months <= 1.5
                        THEN 1
                        ELSE 0
                    END
                ) AS near_term_exposure,
                AVG(months_of_stock_cover)
                    AS average_months_cover
            FROM inventory_optimisation_results
            """
        )

        row = result.iloc[0]

        return {
            "critical_stockouts": int(
                row["critical_stockouts"] or 0
            ),
            "high_stockouts": int(
                row["high_stockouts"] or 0
            ),
            "immediate_exposure": int(
                row["immediate_exposure"] or 0
            ),
            "near_term_exposure": int(
                row["near_term_exposure"] or 0
            ),
            "average_months_cover": float(
                row["average_months_cover"] or 0.0
            ),
        }

    def load_operations_readiness_data(
        self,
    ) -> pd.DataFrame:
        """Load Operations Manager stock-readiness records."""

        return self.query(
            """
            SELECT
                part_number,
                description,
                engineering_criticality,
                stockout_risk,
                current_balance,
                average_monthly_demand,
                months_of_stock_cover,
                estimated_stockout_months,
                reorder_point,
                recommended_order_quantity,
                average_lead_time_days,
                forecast_confidence,
                recommendation_status
            FROM inventory_optimisation_results
            ORDER BY
                CASE stockout_risk
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    ELSE 4
                END,
                estimated_stockout_months,
                part_number
            """
        )

    def load_quality_kpis(self) -> dict[str, int]:
        """Load Quality Manager KPI values."""

        result = self.query(
            """
            SELECT
                COUNT(*) AS order_review_records,
                SUM(
                    CASE
                        WHEN human_approval_required
                        THEN 1
                        ELSE 0
                    END
                ) AS human_approval_records,
                SUM(
                    CASE
                        WHEN forecast_confidence = 'Low'
                        AND recommended_order_quantity > 0
                        THEN 1
                        ELSE 0
                    END
                ) AS low_confidence_orders,
                SUM(
                    CASE
                        WHEN automatic_purchase_order_allowed
                        THEN 1
                        ELSE 0
                    END
                ) AS automatic_actions_allowed
            FROM inventory_optimisation_results
            WHERE recommended_order_quantity > 0
            """
        )

        assurance = self.query(
            """
            SELECT
                SUM(
                    CASE
                        WHEN assurance_status = 'Passed'
                        THEN 1
                        ELSE 0
                    END
                ) AS passed_findings,
                SUM(
                    CASE
                        WHEN assurance_status = 'Failed'
                        THEN 1
                        ELSE 0
                    END
                ) AS failed_findings
            FROM agent_assurance_findings
            """
        ).iloc[0]

        row = result.iloc[0]

        return {
            "order_review_records": int(
                row["order_review_records"] or 0
            ),
            "human_approval_records": int(
                row["human_approval_records"] or 0
            ),
            "low_confidence_orders": int(
                row["low_confidence_orders"] or 0
            ),
            "automatic_actions_allowed": int(
                row["automatic_actions_allowed"] or 0
            ),
            "assurance_passed": int(
                assurance["passed_findings"] or 0
            ),
            "assurance_failed": int(
                assurance["failed_findings"] or 0
            ),
        }

    def load_quality_review_data(
        self,
    ) -> pd.DataFrame:
        """Load Quality Manager review records."""

        return self.query(
            """
            SELECT
                part_number,
                description,
                stockout_risk,
                engineering_criticality,
                forecast_confidence,
                selected_forecast_model,
                recommended_order_quantity,
                procurement_value_usd,
                human_approval_required,
                automatic_purchase_order_allowed,
                recommendation_status
            FROM inventory_optimisation_results
            WHERE recommended_order_quantity > 0
            ORDER BY
                CASE stockout_risk
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    ELSE 4
                END,
                procurement_value_usd DESC
            """
        )
    def load_latest_pipeline_run(
        self,
    ) -> pd.DataFrame:
        """Load the most recently completed pipeline run."""

        if not self.table_exists(
            "pipeline_runs"
        ):
            return pd.DataFrame()

        return self.query(
            """
            SELECT
                pipeline_run_id,
                started_at,
                completed_at,
                duration_seconds,
                overall_status,
                successful_stage_count,
                failed_stage_count
            FROM pipeline_runs
            ORDER BY completed_at DESC
            LIMIT 1
            """
        )

    def load_latest_pipeline_stages(
        self,
    ) -> pd.DataFrame:
        """Load stage results from the latest pipeline run."""

        required_tables = [
            "pipeline_runs",
            "pipeline_stage_runs",
        ]

        if not all(
            self.table_exists(table_name)
            for table_name in required_tables
        ):
            return pd.DataFrame()

        return self.query(
            """
            WITH latest_run AS (
                SELECT pipeline_run_id
                FROM pipeline_runs
                ORDER BY completed_at DESC
                LIMIT 1
            )
            SELECT
                stage_name,
                module_name,
                status,
                started_at,
                completed_at,
                duration_seconds,
                return_code,
                error_message
            FROM pipeline_stage_runs
            WHERE pipeline_run_id = (
                SELECT pipeline_run_id
                FROM latest_run
            )
            ORDER BY started_at
            """
        )

    def load_recent_pipeline_runs(
        self,
        limit: int = 10,
    ) -> pd.DataFrame:
        """Load recent pipeline execution history."""

        if not self.table_exists(
            "pipeline_runs"
        ):
            return pd.DataFrame()

        return self.query(
            """
            SELECT
                pipeline_run_id,
                started_at,
                completed_at,
                duration_seconds,
                overall_status,
                successful_stage_count,
                failed_stage_count
            FROM pipeline_runs
            ORDER BY completed_at DESC
            LIMIT ?
            """,
            [
                int(limit),
            ],
        )

    def load_pipeline_kpis(
        self,
    ) -> dict[str, object]:
        """Load pipeline-monitoring KPI values."""

        latest_run = (
            self.load_latest_pipeline_run()
        )

        latest_stages = (
            self.load_latest_pipeline_stages()
        )

        if latest_run.empty:
            return {
                "pipeline_run_id": None,
                "overall_status": "Unknown",
                "duration_seconds": 0.0,
                "successful_stage_count": 0,
                "failed_stage_count": 0,
                "completed_at": None,
                "slowest_stage": None,
                "slowest_stage_seconds": 0.0,
            }

        run_row = latest_run.iloc[0]

        if latest_stages.empty:
            slowest_stage = None
            slowest_stage_seconds = 0.0
        else:
            slowest_row = (
                latest_stages.sort_values(
                    "duration_seconds",
                    ascending=False,
                )
                .iloc[0]
            )

            slowest_stage = str(
                slowest_row["stage_name"]
            )

            slowest_stage_seconds = float(
                slowest_row[
                    "duration_seconds"
                ]
                or 0.0
            )

        return {
            "pipeline_run_id": str(
                run_row["pipeline_run_id"]
            ),
            "overall_status": str(
                run_row["overall_status"]
            ),
            "duration_seconds": float(
                run_row["duration_seconds"]
                or 0.0
            ),
            "successful_stage_count": int(
                run_row[
                    "successful_stage_count"
                ]
                or 0
            ),
            "failed_stage_count": int(
                run_row[
                    "failed_stage_count"
                ]
                or 0
            ),
            "completed_at": (
                run_row["completed_at"]
            ),
            "slowest_stage": slowest_stage,
            "slowest_stage_seconds": (
                slowest_stage_seconds
            ),
        }

    def load_pipeline_table_status(
        self,
    ) -> pd.DataFrame:
        """Load pipeline source and output table availability."""

        table_names = [
            "inventory",
            "issue_history",
            "repair_orders",
            "forecast_summary",
            "monthly_demand",
            "demand_metrics",
            "forecast_backtest_results",
            "selected_forecast_models",
            "final_part_forecasts",
            "inventory_optimisation_results",
            "procurement_recommendations",
            "agent_recommendations",
            "agent_assurance_findings",
            "pipeline_runs",
            "pipeline_stage_runs",
        ]

        rows: list[dict[str, object]] = []

        for table_name in table_names:
            exists = self.table_exists(
                table_name
            )

            if not exists:
                rows.append(
                    {
                        "table_name": table_name,
                        "row_count": 0,
                        "status": "Missing",
                    }
                )
                continue

            count_result = self.query(
                f"""
                SELECT COUNT(*) AS row_count
                FROM "{table_name}"
                """
            )

            row_count = int(
                count_result.iloc[0][
                    "row_count"
                ]
            )

            rows.append(
                {
                    "table_name": table_name,
                    "row_count": row_count,
                    "status": (
                        "Available"
                        if row_count > 0
                        else "Empty"
                    ),
                }
            )

        return pd.DataFrame(
            rows
        )

    def load_management_drilldown_parts(
        self,
        *,
        stockout_risk: str | None = None,
        engineering_criticality: str | None = None,
        forecast_confidence: str | None = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Load management drill-down spare-part records."""

        conditions = [
            "1 = 1",
        ]

        parameters: list[object] = []

        if stockout_risk:
            conditions.append(
                "stockout_risk = ?"
            )
            parameters.append(
                stockout_risk
            )

        if engineering_criticality:
            conditions.append(
                "engineering_criticality = ?"
            )
            parameters.append(
                engineering_criticality
            )

        if forecast_confidence:
            conditions.append(
                "forecast_confidence = ?"
            )
            parameters.append(
                forecast_confidence
            )

        parameters.append(
            int(limit)
        )

        where_clause = " AND ".join(
            conditions
        )

        return self.query(
            f"""
            SELECT
                part_number,
                description,
                engineering_criticality,
                stockout_risk,
                procurement_priority,
                forecast_confidence,
                selected_forecast_model,
                current_balance,
                average_monthly_demand,
                forecast_3m,
                forecast_6m,
                forecast_12m,
                safety_stock,
                reorder_point,
                months_of_stock_cover,
                estimated_stockout_months,
                recommended_order_quantity,
                procurement_value_usd,
                average_lead_time_days,
                recommendation_status,
                recommendation_reason
            FROM inventory_optimisation_results
            WHERE {where_clause}
            ORDER BY
                procurement_priority,
                procurement_value_usd DESC,
                part_number
            LIMIT ?
            """,
            parameters,
        )

    def load_part_forecast_history(
        self,
        part_number: str,
    ) -> pd.DataFrame:
        """Load historical monthly demand for one spare part."""

        return self.query(
            """
            SELECT
                demand_month,
                quantity_issued,
                issued_value_usd,
                issue_transactions,
                demand_occurred
            FROM monthly_demand
            WHERE part_number = ?
            ORDER BY demand_month
            """,
            [
                part_number,
            ],
        )

    def load_part_agent_advisories(
        self,
        part_number: str,
    ) -> pd.DataFrame:
        """Load assured agent recommendations for one spare part."""

        if not self.table_exists(
            "agent_recommendations"
        ):
            return pd.DataFrame()

        return self.query(
            """
            SELECT
                recommendation_id,
                agent_name,
                target_role,
                recommendation_type,
                priority,
                part_number,
                title,
                recommendation,
                rationale,
                forecast_confidence,
                evidence,
                human_approval_required,
                automatic_action_allowed,
                status,
                assurance_status,
                approved_for_management_display
            FROM agent_recommendations
            WHERE part_number = ?
            AND approved_for_management_display = TRUE
            ORDER BY
                CASE priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END,
                agent_name
            """,
            [
                part_number,
            ],
        )

    def load_part_decision_record(
        self,
        part_number: str,
    ) -> pd.DataFrame:
        """Load the detailed optimisation decision record for one part."""

        return self.query(
            """
            SELECT
                part_number,
                description,
                engineering_criticality,
                demand_pattern,
                selected_forecast_model,
                forecast_confidence,
                current_balance,
                unit_price_usd,
                inventory_value_usd,
                average_monthly_demand,
                demand_standard_deviation,
                forecast_3m,
                forecast_6m,
                forecast_12m,
                average_lead_time_days,
                lead_time_months,
                demand_during_lead_time,
                service_level,
                service_level_z_score,
                safety_stock,
                reorder_point,
                economic_order_quantity,
                target_stock,
                recommended_order_quantity,
                months_of_stock_cover,
                estimated_stockout_months,
                stockout_risk,
                procurement_priority,
                procurement_value_usd,
                automatic_purchase_order_allowed,
                human_approval_required,
                recommendation_status,
                recommendation_reason
            FROM inventory_optimisation_results
            WHERE part_number = ?
            LIMIT 1
            """,
            [part_number],
        )

    def load_selected_forecast_model(
        self,
        part_number: str,
    ) -> dict[str, Any]:
        """Load selected forecast-model evidence."""

        result = self.query(
            """
            SELECT
                part_number,
                description,
                demand_pattern,
                selected_model,
                selection_metric,
                selection_score,
                mae,
                rmse,
                wape,
                bias,
                validation_actual_total,
                validation_forecast_total,
                successful_model_count,
                rejected_model_count,
                forecast_confidence,
                selection_reason
            FROM selected_forecast_models
            WHERE part_number = ?
            """,
            [part_number],
        )

        if result.empty:
            return {}

        return result.iloc[0].to_dict()


    def load_forecast_backtest_results(
        self,
        part_number: str,
    ) -> pd.DataFrame:
        """Load candidate forecast-model results."""

        return self.query(
            """
            SELECT
                model_rank,
                model_name,
                status,
                mae,
                rmse,
                wape,
                bias,
                selected,
                model_parameters
            FROM forecast_backtest_results
            WHERE part_number = ?
            ORDER BY
                model_rank NULLS LAST,
                model_name
            """,
            [part_number],
        )


    def load_part_demand_metrics(
        self,
        part_number: str,
    ) -> dict[str, Any]:
        """Load demand evidence for forecast explainability."""

        result = self.query(
            """
            SELECT
                part_number,
                description,
                history_months,
                total_quantity_issued,
                issue_transactions,
                active_demand_months,
                zero_demand_months,
                average_monthly_demand,
                demand_standard_deviation,
                coefficient_of_variation,
                adi,
                cv_squared,
                demand_pattern,
                xyz_class,
                forecast_eligible,
                demand_frequency_percent
            FROM demand_metrics
            WHERE part_number = ?
            """,
            [part_number],
        )

        if result.empty:
            return {}

        return result.iloc[0].to_dict()

    def load_recommendation_trace(
        self,
        recommendation_id: str,
    ) -> dict[str, Any]:
        """Load one agent recommendation for traceability."""

        result = self.query(
            """
            SELECT
                recommendation_id,
                agent_name,
                target_role,
                recommendation_type,
                priority,
                part_number,
                title,
                recommendation,
                rationale,
                forecast_confidence,
                evidence,
                human_approval_required,
                automatic_action_allowed,
                status,
                assurance_status,
                approved_for_management_display
            FROM agent_recommendations
            WHERE recommendation_id = ?
            LIMIT 1
            """,
            [recommendation_id],
        )

        if result.empty:
            return {}

        return result.iloc[0].to_dict()

    def load_part_recommendation_traces(
        self,
        part_number: str,
    ) -> pd.DataFrame:
        """Load all management-display advisories for one part."""

        return self.query(
            """
            SELECT
                recommendation_id,
                agent_name,
                target_role,
                recommendation_type,
                priority,
                title,
                forecast_confidence,
                status,
                assurance_status,
                approved_for_management_display
            FROM agent_recommendations
            WHERE part_number = ?
            ORDER BY
                CASE priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END,
                agent_name
            """,
            [part_number],
        )

    def load_recommendation_assurance_findings(
        self,
        recommendation_id: str,
    ) -> pd.DataFrame:
        """Load assurance findings for one recommendation."""

        return self.query(
            """
            SELECT
                recommendation_id,
                assurance_status,
                finding_type,
                finding_message,
                evidence_complete,
                governance_compliant,
                approved_for_management_display
            FROM agent_assurance_findings
            WHERE recommendation_id = ?
            ORDER BY
                finding_type,
                finding_message
            """,
            [recommendation_id],
        )

    def load_management_alert_inventory(
        self,
    ) -> pd.DataFrame:
        """Load optimisation evidence used by management alerts."""

        return self.query(
            """
            SELECT
                part_number,
                description,
                engineering_criticality,
                stockout_risk,
                forecast_confidence,
                current_balance,
                recommended_order_quantity,
                procurement_value_usd,
                average_lead_time_days,
                recommendation_status
            FROM inventory_optimisation_results
            ORDER BY
                procurement_priority,
                procurement_value_usd DESC
            """
        )


    def load_management_alert_assurance(
        self,
    ) -> pd.DataFrame:
        """Load agent assurance evidence used by management alerts."""

        return self.query(
            """
            SELECT
                recommendation_id,
                assurance_status,
                finding_type,
                finding_message,
                evidence_complete,
                governance_compliant,
                approved_for_management_display
            FROM agent_assurance_findings
            """
        )

    def load_data_quality_inventory(
        self,
    ) -> pd.DataFrame:
        """Load inventory source data for data-quality monitoring."""

        return self.query(
            """
            SELECT
                no,
                description,
                part_number,
                serial_number,
                unit_price_usd,
                purchased_quantity,
                purchase_order_number,
                total_price_usd,
                purchase_order_date,
                delivery_order_number,
                delivery_order_date,
                batch_number,
                repair_order_number,
                top_assembly_part_number,
                top_assembly_serial_number,
                quantity_issued,
                date_issued,
                balance_quantity,
                repair_order_status,
                record_classification
            FROM inventory
            """
        )


    def load_data_quality_issue_history(
        self,
    ) -> pd.DataFrame:
        """Load issue-history source data for data-quality monitoring."""

        return self.query(
            """
            SELECT
                transaction_id,
                repair_order,
                part_id,
                part_number,
                description,
                issue_date,
                quantity_issued,
                unit_price_usd,
                issued_value_usd,
                top_assembly_part_number,
                top_assembly_serial_number,
                issue_type,
                repair_order_status,
                abc_class,
                engineering_criticality,
                data_classification
            FROM issue_history
            """
        )


    def load_data_quality_repair_orders(
        self,
    ) -> pd.DataFrame:
        """Load repair-order source data for data-quality monitoring."""

        return self.query(
            """
            SELECT
                repair_order,
                part_id,
                part_number,
                description,
                top_assembly_part_number,
                top_assembly_serial_number,
                open_date,
                completion_date,
                repair_order_status,
                maintenance_type,
                operational_priority,
                planned_quantity,
                data_classification
            FROM repair_orders
            """
        )