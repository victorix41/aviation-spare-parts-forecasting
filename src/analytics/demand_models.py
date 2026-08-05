"""Typed result models for demand analytics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DemandAnalyticsSummary:
    """Summary of a completed demand-analysis run."""

    history_start_date: str
    history_end_date: str
    history_months: int
    inventory_record_count: int
    inventory_part_count: int
    active_demand_part_count: int
    no_demand_part_count: int
    monthly_demand_rows: int
    total_quantity_issued: float
    total_issued_value_usd: float
    abc_counts: dict[str, int]
    xyz_counts: dict[str, int]
    demand_pattern_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Convert the summary into a serialisable dictionary."""

        return asdict(self)