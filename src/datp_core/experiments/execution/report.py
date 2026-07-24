"""Experiment execution report."""

from __future__ import annotations

from attrs import define

from datp_core.core.identifiers import ExperimentId
from datp_core.pipeline.stages.outcomes import StageJobOutcome


@define(frozen=True, slots=True, kw_only=True)
class ExperimentExecutionReport:
    experiment_id: ExperimentId
    outcomes: tuple[StageJobOutcome, ...]
    successful_jobs: int
    failed_jobs: int
