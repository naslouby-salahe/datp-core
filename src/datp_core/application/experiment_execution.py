"""Application use cases for experiment execution and resumption."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.application.experiment_planning import PlanExperimentUseCase
from datp_core.domain.identifiers import ExperimentId, RunId
from datp_core.domain.outcomes import JobExecutionStatus, StageJobOutcome


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentExecutionReport:
    run_id: RunId
    experiment_id: ExperimentId
    outcomes: tuple[StageJobOutcome, ...]


class ExecuteExperimentUseCase:
    def __init__(self, planner: PlanExperimentUseCase | None = None) -> None:
        self._planner = planner or PlanExperimentUseCase()

    def execute(self, experiment_id: ExperimentId) -> ExperimentExecutionReport:
        graph = self._planner.execute(experiment_id)
        sorted_jobs = graph.lexicographical_topological_sort()
        outcomes = []

        for job in sorted_jobs:
            outcomes.append(
                StageJobOutcome(
                    job_id=job.job_id,
                    stage=job.stage,
                    status=JobExecutionStatus.SUCCESS,
                    produced_artifact=job.output,
                )
            )

        return ExperimentExecutionReport(
            run_id=RunId(f"run_{experiment_id.value}"),
            experiment_id=experiment_id,
            outcomes=tuple(outcomes),
        )


class ResumeExperimentUseCase:
    def __init__(self, executor: ExecuteExperimentUseCase | None = None) -> None:
        self._executor = executor or ExecuteExperimentUseCase()

    def execute(self, experiment_id: ExperimentId) -> ExperimentExecutionReport:
        return self._executor.execute(experiment_id)
