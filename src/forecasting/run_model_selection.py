"""Run backtesting and automatic forecast-model selection."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import yaml

from src.forecasting.backtesting import (
    run_part_model_selection,
)
from src.forecasting.final_forecast import (
    generate_final_forecast,
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
        settings = yaml.safe_load(file)

    if not isinstance(settings, dict):
        raise ValueError(
            "Settings must be a YAML mapping."
        )

    return settings


def build_model_configurations(
    settings: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build candidate model configurations."""

    forecast_settings = settings[
        "forecast_models"
    ]

    configurations: dict[
        str,
        dict[str, Any],
    ] = {}

    if forecast_settings[
        "naive"
    ]["enabled"]:
        configurations["naive"] = {}

    if forecast_settings[
        "moving_average"
    ]["enabled"]:
        configurations[
            "moving_average"
        ] = {
            "window": int(
                forecast_settings[
                    "moving_average"
                ]["window"]
            )
        }

    if forecast_settings[
        "weighted_moving_average"
    ]["enabled"]:
        configurations[
            "weighted_moving_average"
        ] = {
            "weights": list(
                forecast_settings[
                    "weighted_moving_average"
                ]["weights"]
            )
        }

    if forecast_settings[
        "exponential_smoothing"
    ]["enabled"]:
        configurations[
            "exponential_smoothing"
        ] = {
            "smoothing_level": float(
                forecast_settings[
                    "exponential_smoothing"
                ]["smoothing_level"]
            )
        }

    if forecast_settings[
        "croston_sba"
    ]["enabled"]:
        configurations[
            "croston_sba"
        ] = {
            "alpha": float(
                forecast_settings[
                    "croston_sba"
                ]["alpha"]
            )
        }

    return configurations


def load_forecast_data(
    database_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load demand metrics and monthly demand."""

    if not database_path.is_file():
        raise FileNotFoundError(
            "DuckDB database not found. "
            "Run Phases 2 and 3.1 first."
        )

    with duckdb.connect(
        str(database_path),
        read_only=True,
    ) as connection:
        demand_metrics = connection.execute(
            """
            SELECT *
            FROM demand_metrics
            WHERE forecast_eligible = TRUE
            ORDER BY part_number
            """
        ).fetchdf()

        monthly_demand = connection.execute(
            """
            SELECT *
            FROM monthly_demand
            ORDER BY part_number, demand_month
            """
        ).fetchdf()

    return demand_metrics, monthly_demand


def write_outputs(
    database_path: Path,
    output_frames: dict[str, pd.DataFrame],
) -> None:
    """Write model-selection outputs to DuckDB."""

    with duckdb.connect(
        str(database_path)
    ) as connection:
        for table_name, dataframe in (
            output_frames.items()
        ):
            temporary_name = (
                f"temporary_{table_name}"
            )

            connection.register(
                temporary_name,
                dataframe,
            )

            try:
                connection.execute(
                    f"""
                    CREATE OR REPLACE TABLE
                    "{table_name}"
                    AS
                    SELECT *
                    FROM "{temporary_name}"
                    """
                )
            finally:
                connection.unregister(
                    temporary_name
                )


def save_parquet_outputs(
    output_directory: Path,
    output_frames: dict[str, pd.DataFrame],
) -> None:
    """Save model-selection outputs as Parquet."""

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for output_name, dataframe in (
        output_frames.items()
    ):
        dataframe.to_parquet(
            output_directory
            / f"{output_name}.parquet",
            index=False,
        )


def main() -> None:
    """Run Phase 3.3."""

    settings = load_settings()

    database_path = (
        PROJECT_ROOT
        / settings["paths"]["database"]
    )

    forecast_output_directory = (
        PROJECT_ROOT
        / settings["paths"]["forecasts"]
    )

    reports_directory = (
        PROJECT_ROOT
        / settings["paths"]["reports"]
    )

    selection_settings = settings[
        "model_selection"
    ]

    model_configurations = (
        build_model_configurations(
            settings
        )
    )

    demand_metrics, monthly_demand = (
        load_forecast_data(
            database_path
        )
    )

    all_backtests: list[
        dict[str, Any]
    ] = []

    all_selections: list[
        dict[str, Any]
    ] = []

    all_final_forecasts: list[
        dict[str, Any]
    ] = []

    for metric_row in (
        demand_metrics.itertuples(
            index=False
        )
    ):
        part_number = str(
            metric_row.part_number
        )

        part_history = (
            monthly_demand.loc[
                monthly_demand[
                    "part_number"
                ]
                == part_number
            ]
            .sort_values(
                "demand_month"
            )["quantity_issued"]
            .reset_index(drop=True)
        )

        selection_result = (
            run_part_model_selection(
                part_number=part_number,
                description=str(
                    metric_row.description
                ),
                demand_pattern=str(
                    metric_row.demand_pattern
                ),
                active_demand_months=int(
                    metric_row.active_demand_months
                ),
                demand=part_history,
                validation_months=int(
                    selection_settings[
                        "validation_months"
                    ]
                ),
                minimum_training_months=int(
                    selection_settings[
                        "minimum_training_months"
                    ]
                ),
                model_configurations=(
                    model_configurations
                ),
                primary_metric=str(
                    selection_settings[
                        "primary_metric"
                    ]
                ),
                tie_break_order=list(
                    selection_settings[
                        "tie_break_order"
                    ]
                ),
            )
        )

        for result in (
            selection_result.backtest_results
        ):
            result_record = result.to_dict()
            result_record[
                "model_parameters"
            ] = json.dumps(
                result_record[
                    "model_parameters"
                ],
                sort_keys=True,
            )
            all_backtests.append(
                result_record
            )

        selected = (
            selection_result.selected_model
        )

        if selected is None:
            continue

        all_selections.append(
            selected.to_dict()
        )

        selected_parameters = (
            model_configurations[
                selected.selected_model
            ]
        )

        final_forecast = (
            generate_final_forecast(
                part_number=part_number,
                description=str(
                    metric_row.description
                ),
                demand_pattern=str(
                    metric_row.demand_pattern
                ),
                selected_model=(
                    selected.selected_model
                ),
                forecast_confidence=(
                    selected.forecast_confidence
                ),
                demand=part_history,
                forecast_horizon=int(
                    selection_settings[
                        "final_forecast_horizon_months"
                    ]
                ),
                model_parameters=(
                    selected_parameters
                ),
            )
        )

        final_record = (
            final_forecast.to_dict()
        )

        final_record[
            "forecast_values"
        ] = json.dumps(
            final_record[
                "forecast_values"
            ]
        )

        final_record[
            "model_parameters"
        ] = json.dumps(
            final_record[
                "model_parameters"
            ],
            sort_keys=True,
        )

        all_final_forecasts.append(
            final_record
        )

    backtest_frame = pd.DataFrame(
        all_backtests
    )

    selected_frame = pd.DataFrame(
        all_selections
    )

    final_forecast_frame = pd.DataFrame(
        all_final_forecasts
    )

    output_tables = selection_settings[
        "output_tables"
    ]

    output_frames = {
        output_tables[
            "backtest_results"
        ]: backtest_frame,
        output_tables[
            "selected_models"
        ]: selected_frame,
        output_tables[
            "final_forecasts"
        ]: final_forecast_frame,
    }

    write_outputs(
        database_path,
        output_frames,
    )

    save_parquet_outputs(
        forecast_output_directory,
        output_frames,
    )

    selected_model_counts = Counter(
        selected_frame[
            "selected_model"
        ].tolist()
        if not selected_frame.empty
        else []
    )

    confidence_counts = Counter(
        selected_frame[
            "forecast_confidence"
        ].tolist()
        if not selected_frame.empty
        else []
    )

    summary = {
        "forecast_eligible_parts": int(
            len(demand_metrics)
        ),
        "parts_with_selected_model": int(
            len(selected_frame)
        ),
        "backtest_records": int(
            len(backtest_frame)
        ),
        "candidate_models": list(
            model_configurations
        ),
        "primary_metric": str(
            selection_settings[
                "primary_metric"
            ]
        ),
        "selected_model_counts": dict(
            selected_model_counts
        ),
        "forecast_confidence_counts": dict(
            confidence_counts
        ),
        "success": (
            len(selected_frame)
            == len(demand_metrics)
        ),
    }

    reports_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    with (
        reports_directory
        / "model_selection_summary.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            indent=2,
        )

    separator = "=" * 72

    print(separator)
    print(
        "AVIATION SPARE PARTS — "
        "PHASE 3.3 MODEL SELECTION"
    )
    print(separator)
    print(
        f"Forecast-eligible parts: "
        f"{summary['forecast_eligible_parts']:,}"
    )
    print(
        f"Parts with selected models: "
        f"{summary['parts_with_selected_model']:,}"
    )
    print(
        f"Backtest records: "
        f"{summary['backtest_records']:,}"
    )
    print(
        f"Candidate models per part: "
        f"{len(model_configurations)}"
    )
    print(
        f"Primary metric: "
        f"{summary['primary_metric'].upper()}"
    )
    print(
        "Selected model counts: "
        f"{summary['selected_model_counts']}"
    )
    print(
        "Forecast confidence: "
        f"{summary['forecast_confidence_counts']}"
    )
    print(
        f"Model selection passed: "
        f"{summary['success']}"
    )
    print(separator)


if __name__ == "__main__":
    main()