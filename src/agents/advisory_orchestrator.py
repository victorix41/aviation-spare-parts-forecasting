"""Orchestrate specialist aviation advisory agents."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.agents.advisory_models import (
    AgentRecommendation,
    AssuranceFinding,
)
from src.agents.assurance_agent import (
    run_final_assurance,
)
from src.agents.engineering_agent import (
    generate_engineering_recommendations,
)
from src.agents.executive_agent import (
    generate_executive_recommendations,
)
from src.agents.finance_agent import (
    generate_finance_recommendations,
)
from src.agents.operations_agent import (
    generate_operations_recommendations,
)
from src.agents.procurement_agent import (
    generate_procurement_recommendations,
)
from src.agents.quality_agent import (
    generate_quality_recommendations,
)
from src.agents.advisory_utils import (
    priority_rank,
)


@dataclass(frozen=True)
class AdvisoryOrchestrationResult:
    """Complete multi-agent orchestration result."""

    recommendations: list[AgentRecommendation]
    assurance_findings: list[AssuranceFinding]


def run_advisory_orchestration(
    *,
    optimisation_data: pd.DataFrame,
    procurement_data: pd.DataFrame,
    settings: dict,
) -> AdvisoryOrchestrationResult:
    """Run every specialist agent and final assurance."""

    recommendations: list[
        AgentRecommendation
    ] = []

    recommendations.extend(
        generate_executive_recommendations(
            optimisation_data,
            settings,
        )
    )

    recommendations.extend(
        generate_procurement_recommendations(
            procurement_data,
            settings,
        )
    )

    recommendations.extend(
        generate_finance_recommendations(
            optimisation_data,
            settings,
        )
    )

    recommendations.extend(
        generate_engineering_recommendations(
            optimisation_data,
            settings,
        )
    )

    recommendations.extend(
        generate_operations_recommendations(
            optimisation_data,
            settings,
        )
    )

    recommendations.extend(
        generate_quality_recommendations(
            optimisation_data,
            settings,
        )
    )

    recommendations = sorted(
        recommendations,
        key=lambda recommendation: (
            priority_rank(
                recommendation.priority
            ),
            recommendation.target_role,
            recommendation.part_number or "",
        ),
    )

    assurance_findings = run_final_assurance(
        recommendations,
        settings,
    )

    return AdvisoryOrchestrationResult(
        recommendations=recommendations,
        assurance_findings=assurance_findings,
    )