"""Experiment execution report."""

from __future__ import annotations

from attrs import define

from datp_core.core.identifiers import ExperimentId, RunId
from datp_core.pipeline.stages.outcomes import StageJobOutcome


@define(frozen=True, slots=True, kw_only=True)
class ExperimentExecutionReport:
    run_id: RunId
    experiment_id: ExperimentId
    outcomes: tuple[StageJobOutcome, ...]
    successful_jobs: int
    reused_jobs: int
    failed_jobs: int
