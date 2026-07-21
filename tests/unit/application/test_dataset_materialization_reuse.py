"""Dataset materialization resumes only from the matching immutable artifact."""

from pathlib import Path

from datp_core.application.experiment_planning import PlanExperimentUseCase
from datp_core.application.stage_handlers import DatasetMaterializationStageHandler
from datp_core.composition.root import _build_adapter_registry, build_application
from datp_core.domain.artifacts import (
    ArtifactCommitMetadata,
    ArtifactCommitRequest,
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    ArtifactParent,
    BytesPayload,
)
from datp_core.domain.identifiers import ArtifactId, ExperimentId, RunId
from datp_core.domain.outcomes import JobExecutionStatus, StageKind
from datp_core.infrastructure.artifacts.atomic_commit import AtomicArtifactRepository


def test_materialization_reuses_a_matching_frozen_artifact_without_reading_raw_sources(tmp_path: Path) -> None:
    app = build_application()
    job = next(
        planned
        for planned in PlanExperimentUseCase(app.config).execute(ExperimentId("anchor_reproduction")).jobs
        if planned.stage is StageKind.DATASET_MATERIALIZATION
    )
    run_id = RunId(f"run_anchor_reproduction_{app.config.execution_fingerprint.value[:12]}")
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    relative_path = f"runs/{run_id.value}/{job.job_id.value}"
    manifest_relative_path = f"{relative_path}.split_manifest"
    readiness_relative_path = f"{relative_path}.readiness"
    manifest_key = ArtifactKey(
        artifact_id=ArtifactId(f"{job.output.artifact_id.value}:split_manifest"),
        kind=ArtifactKind.SPLIT_MANIFEST,
    )
    readiness_key = ArtifactKey(
        artifact_id=ArtifactId(f"{job.output.artifact_id.value}:readiness"),
        kind=ArtifactKind.DATASET_READINESS,
    )
    assert repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=readiness_key,
                artifact_format=ArtifactFormat.JSON,
                scientific_fingerprint=app.config.scientific_fingerprint,
                execution_fingerprint=app.config.execution_fingerprint,
                relative_path=readiness_relative_path,
                parents=(
                    ArtifactParent(parent_key=job.output, scientific_fingerprint=app.config.scientific_fingerprint),
                ),
                schema_version=1,
                creation_timestamp=1.0,
                environment_identity="test",
            ),
            payload=BytesPayload(payload_bytes=b"readiness"),
        )
    ).success
    assert repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=manifest_key,
                artifact_format=ArtifactFormat.JSON,
                scientific_fingerprint=app.config.scientific_fingerprint,
                execution_fingerprint=app.config.execution_fingerprint,
                relative_path=manifest_relative_path,
                parents=(
                    ArtifactParent(parent_key=job.output, scientific_fingerprint=app.config.scientific_fingerprint),
                ),
                schema_version=1,
                creation_timestamp=1.0,
                environment_identity="test",
            ),
            payload=BytesPayload(payload_bytes=b"split manifest"),
        )
    ).success
    assert repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=job.output,
                artifact_format=ArtifactFormat.PARQUET,
                scientific_fingerprint=app.config.scientific_fingerprint,
                execution_fingerprint=app.config.execution_fingerprint,
                relative_path=relative_path,
                parents=(),
                schema_version=1,
                creation_timestamp=1.0,
                environment_identity="test",
            ),
            payload=BytesPayload(payload_bytes=b"already materialized"),
        )
    ).success
    outcome = DatasetMaterializationStageHandler(app.config, repository, _build_adapter_registry()).execute(job, run_id)
    assert outcome.status is JobExecutionStatus.REUSED
    assert outcome.produced_artifact == job.output
