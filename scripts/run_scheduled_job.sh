#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$HOME/Personal Projects/aviation-spare-parts-forecasting"
CONDA_ENV="spare-parts-ai"

cd "$PROJECT_DIR"

source "$HOME/miniconda3/etc/profile.d/conda.sh"

conda activate "$CONDA_ENV"

python -m src.scheduling.run_scheduled_job