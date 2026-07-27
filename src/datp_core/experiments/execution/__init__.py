"""Experiment execution: runner, campaign, report, preflight handler, output manager."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.core.identifiers import ExperimentId
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class ExperimentExecutionReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    experiment_id: ExperimentId
    outcomes: tuple[StageJobOutcome, ...]
    successful_jobs: int
    failed_jobs: int


from datp_core.experiments.execution.campaign import CampaignExperimentResult, CampaignReport, CampaignRunner
from datp_core.experiments.execution.output_manager import (
    ExperimentManifest,
    ExperimentOutputManager,
    ExperimentStatus,
    OutputInspection,
    OutputState,
)
from datp_core.experiments.execution.preflight import PreflightStageHandler
from datp_core.experiments.execution.runner import (
    ExecuteExperimentUseCase,
    ExperimentRunner,
    ExperimentRunResult,
    ExperimentRunStatus,
)

__all__ = [
    "CampaignExperimentResult",
    "CampaignReport",
    "CampaignRunner",
    "ExecuteExperimentUseCase",
    "ExperimentExecutionReport",
    "ExperimentManifest",
    "ExperimentOutputManager",
    "ExperimentRunResult",
    "ExperimentRunStatus",
    "ExperimentRunner",
    "ExperimentStatus",
    "OutputInspection",
    "OutputState",
    "PreflightStageHandler",
]
