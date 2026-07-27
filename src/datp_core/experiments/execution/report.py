"""Experiment execution report."""

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
