"""Typed result models for inventory optimisation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class InventoryOptimisationResult:
    """Inventory optimisation result for one spare part."""

    part_number: str
    description: str
    engineering_criticality: str
    demand_pattern: str
    selected_forecast_model: str
    forecast_confidence: str

    inventory_record_count: int
    current_balance: float
    unit_price_usd: float
    inventory_value_usd: float

    average_monthly_demand: float
    demand_standard_deviation: float
    forecast_3m: float
    forecast_6m: float
    forecast_12m: float

    average_lead_time_days: float
    lead_time_months: float
    demand_during_lead_time: float
    service_level: float
    service_level_z_score: float

    safety_stock: float
    reorder_point: float
    economic_order_quantity: float
    target_stock: float
    recommended_order_quantity: float

    months_of_stock_cover: float | None
    estimated_stockout_months: float | None
    stockout_risk: str
    procurement_priority: int
    procurement_value_usd: float

    automatic_purchase_order_allowed: bool
    human_approval_required: bool
    recommendation_status: str
    recommendation_reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the result into a serialisable dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class InventoryOptimisationSummary:
    """Summary of an inventory-optimisation run."""

    inventory_parts: int
    forecast_parts: int
    optimisation_records: int
    procurement_recommendations: int
    total_inventory_value_usd: float
    total_recommended_order_quantity: float
    total_procurement_value_usd: float
    risk_counts: dict[str, int]
    priority_counts: dict[str, int]
    human_approval_required_count: int
    success: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert the summary into a serialisable dictionary."""

        return asdict(self)