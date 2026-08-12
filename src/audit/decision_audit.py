"""Append-only management decision audit trail."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid

import duckdb
import pandas as pd


class DecisionAuditError(RuntimeError):
    """Raised when management decision auditing fails."""


class DecisionAuditRepository:
    """Store management decisions separately from analytics data."""

    def __init__(
        self,
        database_path: Path,
    ) -> None:
        """Initialise the audit repository."""

        self.database_path = Path(
            database_path
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.initialise()

    def initialise(self) -> None:
        """Create the append-only audit table."""

        try:
            with duckdb.connect(
                str(
                    self.database_path
                )
            ) as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS
                    management_decision_audit (
                        audit_id VARCHAR NOT NULL,
                        recorded_at TIMESTAMP NOT NULL,
                        recommendation_id VARCHAR NOT NULL,
                        part_number VARCHAR,
                        agent_name VARCHAR,
                        target_role VARCHAR,
                        recommendation_type VARCHAR,
                        priority VARCHAR,
                        assurance_status VARCHAR,
                        forecast_confidence VARCHAR,
                        management_decision VARCHAR NOT NULL,
                        decision_reason VARCHAR NOT NULL,
                        reviewer_reference VARCHAR,
                        human_approval_required BOOLEAN,
                        automatic_action_allowed BOOLEAN,
                        source_status VARCHAR,
                        source_snapshot VARCHAR
                    )
                    """
                )

        except Exception as exc:
            raise DecisionAuditError(
                "Unable to initialise the "
                f"management audit database: {exc}"
            ) from exc

    def record_decision(
        self,
        *,
        recommendation: dict[str, Any],
        management_decision: str,
        decision_reason: str,
        reviewer_reference: str | None = None,
    ) -> str:
        """Append one explicit human management decision."""

        allowed_decisions = {
            "Accepted",
            "Deferred",
            "Rejected",
        }

        if (
            management_decision
            not in allowed_decisions
        ):
            raise DecisionAuditError(
                "Unsupported management decision."
            )

        reason = decision_reason.strip()

        if not reason:
            raise DecisionAuditError(
                "A management decision reason "
                "is required."
            )

        recommendation_id = str(
            recommendation.get(
                "recommendation_id"
            )
            or ""
        ).strip()

        if not recommendation_id:
            raise DecisionAuditError(
                "Recommendation ID is required "
                "for audit recording."
            )

        audit_id = (
            "AUD-"
            + uuid.uuid4().hex[
                :12
            ].upper()
        )

        recorded_at = datetime.now(
            timezone.utc
        )

        source_snapshot = repr(
            recommendation
        )

        try:
            with duckdb.connect(
                str(
                    self.database_path
                )
            ) as connection:
                connection.execute(
                    """
                    INSERT INTO
                        management_decision_audit
                    (
                        audit_id,
                        recorded_at,
                        recommendation_id,
                        part_number,
                        agent_name,
                        target_role,
                        recommendation_type,
                        priority,
                        assurance_status,
                        forecast_confidence,
                        management_decision,
                        decision_reason,
                        reviewer_reference,
                        human_approval_required,
                        automatic_action_allowed,
                        source_status,
                        source_snapshot
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    [
                        audit_id,
                        recorded_at,
                        recommendation_id,
                        recommendation.get(
                            "part_number"
                        ),
                        recommendation.get(
                            "agent_name"
                        ),
                        recommendation.get(
                            "target_role"
                        ),
                        recommendation.get(
                            "recommendation_type"
                        ),
                        recommendation.get(
                            "priority"
                        ),
                        recommendation.get(
                            "assurance_status"
                        ),
                        recommendation.get(
                            "forecast_confidence"
                        ),
                        management_decision,
                        reason,
                        (
                            reviewer_reference
                            or None
                        ),
                        recommendation.get(
                            "human_approval_required"
                        ),
                        recommendation.get(
                            "automatic_action_allowed"
                        ),
                        recommendation.get(
                            "status"
                        ),
                        source_snapshot,
                    ],
                )

        except Exception as exc:
            raise DecisionAuditError(
                "Unable to record management "
                f"decision: {exc}"
            ) from exc

        return audit_id

    def load_history(
        self,
        *,
        recommendation_id: str | None = None,
        part_number: str | None = None,
    ) -> pd.DataFrame:
        """Load management decision audit history."""

        sql = """
            SELECT
                audit_id,
                recorded_at,
                recommendation_id,
                part_number,
                agent_name,
                target_role,
                recommendation_type,
                priority,
                assurance_status,
                forecast_confidence,
                management_decision,
                decision_reason,
                reviewer_reference,
                human_approval_required,
                automatic_action_allowed,
                source_status
            FROM management_decision_audit
        """

        conditions: list[str] = []
        parameters: list[object] = []

        if recommendation_id:
            conditions.append(
                "recommendation_id = ?"
            )
            parameters.append(
                recommendation_id
            )

        if part_number:
            conditions.append(
                "part_number = ?"
            )
            parameters.append(
                part_number
            )

        if conditions:
            sql += (
                " WHERE "
                + " AND ".join(
                    conditions
                )
            )

        sql += (
            " ORDER BY recorded_at DESC"
        )

        try:
            with duckdb.connect(
                str(
                    self.database_path
                ),
                read_only=True,
            ) as connection:
                return connection.execute(
                    sql,
                    parameters,
                ).fetchdf()

        except Exception as exc:
            raise DecisionAuditError(
                "Unable to load management "
                f"decision history: {exc}"
            ) from exc

    def load_all_history(
        self,
    ) -> pd.DataFrame:
        """Load the complete management decision audit history."""

        return self.load_history()