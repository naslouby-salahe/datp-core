"""Pipeline runner, stage-handler protocol, and shared artifact-commit plumbing.

The runner owns only "how a DAG of stage jobs gets walked" -- it has no knowledge of experiments,
datasets, or any other feature concept. What to run is decided by experiments/execution.py.

Deliberately thin: git/VCS lookup lives in artifacts/repository.py, statistical correction lives in
analysis/execution.py, dataset-eligibility-gate evaluation lives in data/readiness.py, and
partition-seed-contract resolution lives in experiments/planning.py -- none of that belongs here.
"""

from __future__ import annotations

from collections.abc import Mapping
from time import time
from typing import Protocol

from datp_core.artifacts.models import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactCommitResult,
    ArtifactFormat,
    ArtifactKey,
    ArtifactParent,
    ArtifactRepository,
    BytesPayload,
    FilePayload,
)
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import JobId, RunId
from datp_core.core.values import Seed
from datp_core.pipeline.models import (
    JobExecutionStatus,
    PlanningGraph,
    StageJob,
    StageJobContext,
    StageJobOutcome,
    StageKind,
)


class StageHandler(Protocol):
    """One executable stage that may only report success after an artifact commit."""

    stage: StageKind

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome: ...


def commit_artifact(
    repository: ArtifactRepository,
    config: ResolvedProjectConfiguration,
    context: StageJobContext,
    *,
    artifact_key: ArtifactKey,
    artifact_format: ArtifactFormat,
    relative_path: str,
    parents: tuple[ArtifactParent, ...],
    payload: BytesPayload | FilePayload,
) -> ArtifactCommitResult:
    return repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=artifact_key,
                artifact_format=artifact_format,
                scientific_fingerprint=config.scientific_fingerprint,
                execution_fingerprint=config.execution_fingerprint,
                relative_path=relative_path,
                parents=parents,
                schema_version=1,
                creation_timestamp=time(),
                environment_identity=config.runtime.bootstrap.environment_identity,
                experiment_id=context.experiment_id,
                seed=Seed(context.seed) if context.seed is not None else None,
            ),
            payload=payload,
        )
    )


def artifact_parents(
    config: ResolvedProjectConfiguration, artifacts: tuple[ArtifactKey, ...]
) -> tuple[ArtifactParent, ...]:
    return tuple(
        ArtifactParent(parent_key=artifact, scientific_fingerprint=config.scientific_fingerprint)
        for artifact in artifacts
    )


def _execute_or_fail(handler: StageHandler | None, job: StageJob, run_id: RunId) -> StageJobOutcome:
    """Execute a handler or return a failure outcome if no handler is registered."""
    if handler is not None:
        return handler.execute(job, run_id)
    return StageJobOutcome.failed(
        job_id=job.job_id,
        stage=job.stage,
        error_message="No stage handler is registered",
    )


def run_planning_graph(
    graph: PlanningGraph,
    handlers: Mapping[StageKind, StageHandler],
    run_id: RunId,
) -> tuple[StageJobOutcome, ...]:
    """Execute every job in the graph's topological order, skipping jobs whose dependencies failed."""
    sorted_jobs = graph.lexicographical_topological_sort()
    outcomes: list[StageJobOutcome] = []
    outcomes_by_job_id: dict[JobId, StageJobOutcome] = {}

    for job in sorted_jobs:
        unavailable_dependencies = tuple(
            dependency
            for dependency in job.dependencies
            if outcomes_by_job_id[dependency].status not in (JobExecutionStatus.SUCCESS, JobExecutionStatus.REUSED)
        )
        handler = handlers.get(job.stage)
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
            else _execute_or_fail(handler, job, run_id)
        )
        outcomes.append(outcome)
        outcomes_by_job_id[job.job_id] = outcome

    return tuple(outcomes)
