"""Shared utilities for advisory agents."""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
import pandas as pd

from src.agents.advisory_models import EvidenceItem


class AdvisoryError(ValueError):
    """Raised when an advisory recommendation cannot be created."""


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """Convert a value safely to float."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    if not np.isfinite(number):
        return default

    return number


def safe_text(
    value: Any,
    default: str = "Unspecified",
) -> str:
    """Convert a value safely to clean text."""

    if value is None or pd.isna(value):
        return default

    text = str(value).strip()

    return text or default


def create_recommendation_id(
    *,
    agent_name: str,
    recommendation_type: str,
    part_number: str | None,
    sequence: int,
) -> str:
    """Create a stable recommendation identifier."""

    raw_value = (
        f"{agent_name}|{recommendation_type}|"
        f"{part_number or 'PORTFOLIO'}|{sequence}"
    )

    digest = hashlib.sha256(
        raw_value.encode("utf-8")
    ).hexdigest()[:10].upper()

    return f"REC-{digest}"


def evidence(
    field_name: str,
    value: Any,
    source_table: str,
) -> EvidenceItem:
    """Create a traceable evidence item."""

    return EvidenceItem(
        field_name=field_name,
        value=value,
        source_table=source_table,
    )


def priority_rank(priority: str) -> int:
    """Return a numerical ranking for recommendation priority."""

    mapping = {
        "Critical": 1,
        "High": 2,
        "Medium": 3,
        "Low": 4,
    }

    return mapping.get(
        priority,
        5,
    )