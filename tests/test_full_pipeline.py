"""Tests for the end-to-end pipeline orchestrator."""

from src.pipeline.run_full_pipeline import (
    PIPELINE_STAGES,
)


def test_pipeline_stage_order() -> None:
    """Pipeline stages should run in dependency order."""

    modules = [
        module_name
        for _, module_name
        in PIPELINE_STAGES
    ]

    assert modules == [
        "src.data.ingestion_pipeline",
        "src.analytics.run_demand_analysis",
        "src.forecasting.run_model_selection",
        "src.optimisation.run_inventory_optimisation",
        "src.agents.run_advisory_engine",
    ]


def test_pipeline_has_unique_modules() -> None:
    """A module should not be executed more than once."""

    modules = [
        module_name
        for _, module_name
        in PIPELINE_STAGES
    ]

    assert len(modules) == len(
        set(modules)
    )