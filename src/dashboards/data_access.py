"""Read-only DuckDB access for management dashboards."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
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
    