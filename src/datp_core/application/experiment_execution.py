"""Application use cases for experiment execution and resumption."""

from __future__ import annotations

from attrs import define

from datp_core.application.experiment_planning import PlanExperimentUseCase
from datp_core.application.stage_handlers import StageHandler
from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.identifiers import ExperimentId, JobId, RunId
from datp_core.domain.outcomes import JobExecutionStatus, StageJobOutcome


@define(frozen=True, slots=True, kw_only=True)
class ExperimentExecutionReport:
    run_id: RunId
    experiment_id: ExperimentId
    outcomes: tuple[StageJobOutcome, ...]
    successful_jobs: int
    reused_jobs: int
    failed_jobs: int


class ExecuteExperimentUseCase:
    """Use case executing real DATP pipeline stage jobs derived from an experiment plan."""

    def __init__(self, config: ResolvedProjectConfiguration, handlers: tuple[StageHandler, ...]) -> None:
        self._config = config
        self._planner = PlanExperimentUseCase(config=self._config)
        self._handlers = {handler.stage: handler for handler in handlers}

    def execute(self, experiment_id: ExperimentId) -> ExperimentExecutionReport:
        graph = self._planner.execute(experiment_id)
        sorted_jobs = graph.lexicographical_topological_sort()
        outcomes: list[StageJobOutcome] = []
        outcomes_by_job_id: dict[JobId, StageJobOutcome] = {}
        successful_cnt = 0
        reused_cnt = 0
        failed_cnt = 0

        # Run ID tied collision-safely to scientific and execution identity
        exec_hash = self._config.execution_fingerprint.value[:12]
        run_id = RunId(f"run_{experiment_id.value}_{exec_hash}")

        for job in sorted_jobs:
            unavailable_dependencies = tuple(
                dependency
                for dependency in job.dependencies
                if outcomes_by_job_id[dependency].status not in (JobExecutionStatus.SUCCESS, JobExecutionStatus.REUSED)
            )
            handler = self._handlers.get(job.stage)
            outcome = (
                StageJobOutcome.skipped(
                    job_id=job.job_id,
                    stage=job.stage,
                    error_message=(
                        "Unavailable prerequisite jobs: "
                        + ", ".join(dependency.value for dependency in unavailable_dependencies)
                    ),
                )
                if unavailable_dependencies
                else handler.execute(job, run_id)
                if handler is not None
                else StageJobOutcome.failed(
                    job_id=job.job_id,
                    stage=job.stage,
                    error_message="No stage handler is registered",
                )
            )
            outcomes.append(outcome)
            outcomes_by_job_id[job.job_id] = outcome
            successful_cnt += outcome.status is JobExecutionStatus.SUCCESS
            reused_cnt += outcome.status is JobExecutionStatus.REUSED
            failed_cnt += outcome.status is JobExecutionStatus.FAILED

        return ExperimentExecutionReport(
            run_id=run_id,
            experiment_id=experiment_id,
            outcomes=tuple(outcomes),
            successful_jobs=successful_cnt,
            reused_jobs=reused_cnt,
            failed_jobs=failed_cnt,
        )
