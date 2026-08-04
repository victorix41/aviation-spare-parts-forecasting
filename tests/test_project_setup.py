"""Tests for the initial project structure."""

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_required_directories_exist() -> None:
    """Confirm that the main project directories have been created."""

    required_directories = [
        "config",
        "data/raw",
        "data/cleaned",
        "data/synthetic",
        "data/processed",
        "database",
        "docs",
        "outputs/forecasts",
        "outputs/reports",
        "outputs/exports",
        "src/data",
        "src/validation",
        "src/analytics",
        "src/forecasting",
        "src/optimisation",
        "src/agents",
        "src/dashboards",
        "src/reports",
        "src/utils",
    ]

    for directory in required_directories:
        path = PROJECT_ROOT / directory
        assert path.is_dir(), f"Required directory is missing: {directory}"


def test_settings_file_can_be_loaded() -> None:
    """Confirm that the YAML settings file is valid."""

    settings_path = PROJECT_ROOT / "config" / "settings.yaml"

    with settings_path.open("r", encoding="utf-8") as file:
        settings = yaml.safe_load(file)

    assert settings["project"]["name"] == "aviation-spare-parts-forecasting"
    assert settings["governance"]["allow_automatic_purchase_orders"] is False
    assert settings["governance"]["require_human_approval"] is True


def test_application_file_exists() -> None:
    """Confirm that the Streamlit application entry point exists."""

    assert (PROJECT_ROOT / "app.py").is_file()