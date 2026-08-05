"""Run the Phase 3.2 forecast model library on one spare part."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import yaml

from src.forecasting.model_registry import (
    run_registered_model,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_settings() -> dict[str, Any]:
    """Load project settings."""

    settings_path = (
        PROJECT_ROOT
        / "config"
        / "settings.yaml"
    )

    with settings_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        settings = yaml.safe_load(
            file
        )

    if not isinstance(
        settings,
        dict,
    ):
        raise ValueError(
            "Settings must be a YAML mapping."
        )

    return settings


def load_demonstration_part(
    database_path: Path,
) -> tuple[str, str, pd.Series]:
    """Load the highest-value forecast-eligible part."""

    if not database_path.is_file():
        raise FileNotFoundError(
            "DuckDB database not found. "
            "Run Phases 2 and 3.1 first."
        )

    with duckdb.connect(
        str(database_path),
        read_only=True,
    ) as connection:
        part_record = connection.execute(
            """
            SELECT
                part_number,
                description
            FROM demand_metrics
            WHERE forecast_eligible = TRUE
            ORDER BY total_issued_value_usd DESC
            LIMIT 1
            """
        ).fetchone()

        if part_record is None:
            raise ValueError(
                "No forecast-eligible part was found."
            )

        part_number = str(
            part_record[0]
        )

        description = str(
            part_record[1]
        )

        demand = connection.execute(
            """
            SELECT
                quantity_issued
            FROM monthly_demand
            WHERE part_number = ?
            ORDER BY demand_month
            """,
            [part_number],
        ).fetchdf()[
            "quantity_issued"
        ]

    return (
        part_number,
        description,
        demand,
    )


def main() -> None:
    """Run every Phase 3.2 model for one part."""

    settings = load_settings()

    database_path = (
        PROJECT_ROOT
        / settings["paths"]["database"]
    )

    model_settings = settings[
        "forecast_models"
    ]

    forecast_horizon = int(
        model_settings[
            "forecast_horizon_months"
        ]
    )

    (
        part_number,
        description,
        demand,
    ) = load_demonstration_part(
        database_path
    )

    model_configurations = {
        "naive": {},
        "moving_average": {
            "window": int(
                model_settings[
                    "moving_average"
                ]["window"]
            ),
        },
        "weighted_moving_average": {
            "weights": list(
                model_settings[
                    "weighted_moving_average"
                ]["weights"]
            ),
        },
        "exponential_smoothing": {
            "smoothing_level": float(
                model_settings[
                    "exponential_smoothing"
                ]["smoothing_level"]
            ),
        },
        "croston_sba": {
            "alpha": float(
                model_settings[
                    "croston_sba"
                ]["alpha"]
            ),
        },
    }

    separator = "=" * 72

    print(separator)
    print(
        "AVIATION SPARE PARTS — "
        "PHASE 3.2 FORECAST MODEL LIBRARY"
    )
    print(separator)
    print(
        f"Part number: {part_number}"
    )
    print(
        f"Description: {description}"
    )
    print(
        f"History months: {len(demand)}"
    )
    print(
        f"Total historical demand: "
        f"{demand.sum():,.0f}"
    )
    print(
        f"Forecast horizon: "
        f"{forecast_horizon} months"
    )
    print()

    for (
        model_name,
        parameters,
    ) in model_configurations.items():
        result = run_registered_model(
            model_name=model_name,
            demand=demand,
            forecast_horizon=forecast_horizon,
            model_parameters=parameters,
        )

        monthly_forecast = float(
            result.forecast_values.iloc[0]
        )

        total_forecast = float(
            result.forecast_values.sum()
        )

        print(
            f"{model_name:<28} "
            f"monthly={monthly_forecast:>10.3f} "
            f"12M total={total_forecast:>10.3f}"
        )

    print(separator)


if __name__ == "__main__":
    main()