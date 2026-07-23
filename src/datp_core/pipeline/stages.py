"""Shared stage-handler protocol and common artifact-commit plumbing used by every feature-owned stage.

Deliberately thin: git/VCS lookup lives in artifacts/provenance.py, statistical correction lives in
analysis/execution.py, dataset-eligibility-gate evaluation lives in datasets/readiness.py, and
partition-seed-contract resolution lives in experiments/planning.py -- none of that belongs here.
"""

from __future__ import annotations

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
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.pipeline.identifiers import RunId
from datp_core.pipeline.models import StageJob, StageJobContext, StageJobOutcome, StageKind
from datp_core.pipeline.values import Seed


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
