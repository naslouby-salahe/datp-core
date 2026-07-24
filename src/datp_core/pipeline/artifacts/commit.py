"""Artifact commit construction — one focused conversion from context to commit request."""

from __future__ import annotations

from collections.abc import Callable
from time import time as _system_time

from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey
from datp_core.artifacts.lineage import ArtifactParent
from datp_core.artifacts.payloads import ArtifactCommitMetadata, ArtifactCommitRequest, BytesPayload, FilePayload
from datp_core.artifacts.repository.models import ArtifactCommitResult
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.hashing import Checksum
from datp_core.core.seeding import Seed
from datp_core.pipeline.artifacts.lineage import verify_parent_lineage
from datp_core.pipeline.stages.context import StageJobContext

_SCHEMA_VERSION = 2


def _default_clock() -> float:
    return _system_time()


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
    clock: Callable[[], float] = _default_clock,
    source_inventory_fingerprint: Checksum | None = None,
) -> ArtifactCommitResult:
    lineage_error = verify_parent_lineage(repository, parents)
    if lineage_error is not None:
        return ArtifactCommitResult(success=False, error_message=lineage_error)
    return repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=artifact_key,
                artifact_format=artifact_format,
                scientific_fingerprint=config.scientific_fingerprint,
                execution_fingerprint=config.execution_fingerprint,
                relative_path=relative_path,
                parents=parents,
                schema_version=_SCHEMA_VERSION,
                creation_timestamp=clock(),
                environment_identity=config.runtime.bootstrap.environment_identity,
                experiment_id=context.experiment_id,
                seed=Seed(context.seed) if context.seed is not None else None,
                source_inventory_fingerprint=source_inventory_fingerprint,
            ),
            payload=payload,
        )
    )
