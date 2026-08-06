"""Models used by the end-to-end pipeline orchestrator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PipelineStageResult:
    """Execution result for one pipeline stage."""

    stage_name: str
    module_name: str
    status: str
    started_at: str
    completed_at: str
    duration_seconds: float
    return_code: int
    error_message: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""

        return asdict(self)


@dataclass(frozen=True)
class PipelineRunSummary:
    """Summary for a complete pipeline execution."""

    pipeline_run_id: str
    started_at: str
    completed_at: str
    duration_seconds: float
    overall_status: str
    successful_stage_count: int
    failed_stage_count: int
    stages: list[PipelineStageResult]

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""

        result = asdict(self)

        result["stages"] = [
            stage.to_dict()
            for stage in self.stages
        ]

        return result