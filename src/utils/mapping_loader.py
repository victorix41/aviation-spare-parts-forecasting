"""Load and validate workbook mapping configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MAPPING_PATH = (
    PROJECT_ROOT
    / "config"
    / "workbook_mapping.yaml"
)


class MappingConfigurationError(RuntimeError):
    """Raised when workbook mapping configuration is invalid."""


def load_workbook_mapping(
    mapping_path: Path | None = None,
) -> dict[str, Any]:
    """Load workbook mapping configuration."""

    resolved_path = (
        mapping_path
        if mapping_path is not None
        else DEFAULT_MAPPING_PATH
    )

    if not resolved_path.is_file():
        raise MappingConfigurationError(
            f"Workbook mapping file not found: {resolved_path}"
        )

    try:
        with resolved_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            mapping = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise MappingConfigurationError(
            f"Invalid YAML in mapping file: {resolved_path}"
        ) from exc

    if not isinstance(mapping, dict):
        raise MappingConfigurationError(
            "Workbook mapping must be a YAML mapping."
        )

    if "workbook" not in mapping:
        raise MappingConfigurationError(
            "Mapping is missing the 'workbook' section."
        )

    if "datasets" not in mapping:
        raise MappingConfigurationError(
            "Mapping is missing the 'datasets' section."
        )

    if not isinstance(mapping["datasets"], dict):
        raise MappingConfigurationError(
            "'datasets' must be a YAML mapping."
        )

    return mapping