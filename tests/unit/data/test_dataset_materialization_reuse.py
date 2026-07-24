"""Dataset materialization resumes only from the matching immutable artifact."""

from pathlib import Path

from datp_core.app import _build_adapter_registry, build_application
from datp_core.artifacts.codecs.manifest import CURRENT_ARTIFACT_SCHEMA_VERSION
from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey, ArtifactKind
from datp_core.artifacts.lineage import ArtifactParent
from datp_core.artifacts.payloads import ArtifactCommitMetadata, ArtifactCommitRequest, BytesPayload
from datp_core.artifacts.repository.filesystem import AtomicArtifactRepository
from datp_core.core.identifiers import ArtifactId, DatasetId, ExperimentId, RunId
from datp_core.data.materialization import DatasetMaterializationStageHandler
from datp_core.data.sources.inventory import build_source_inventory
from datp_core.experiments.planning import expand_experiment_jobs
from datp_core.pipeline.stages.enums import JobExecutionStatus, StageKind


def test_materialization_reuses_a_matching_frozen_artifact_without_reading_raw_sources(tmp_path: Path) -> None:
    app = build_application()
    job = next(
        planned
        for planned in expand_experiment_jobs(
            app.config.experiments.get(ExperimentId("anchor_reproduction")), app.config
        ).jobs
        if planned.stage is StageKind.DATASET_MATERIALIZATION
    )
    experiment = app.config.experiments.get(ExperimentId("anchor_reproduction"))
    population = app.config.populations.get(job.context.population_id or experiment.population_ids[0])
    dataset = app.config.datasets[DatasetId(population.dataset_id.value)]
    # The reuse decision requires the caller's freshly computed source-inventory fingerprint to
    # match what a committed artifact was actually frozen with -- a manually committed artifact
    # with no source fingerprint (or a stale one) is correctly a non-match, not a reusable primary.
    source_fingerprint = build_source_inventory(dataset).fingerprint()
    run_id = RunId(f"run_anchor_reproduction_{app.config.execution_fingerprint.value[:12]}")
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    relative_path = f"runs/{run_id.value}/{job.job_id.value}"
    manifest_relative_path = f"{relative_path}.split_manifest"
    readiness_relative_path = f"{relative_path}.readiness"
    preprocessing_relative_path = f"{relative_path}.preprocessing"
    manifest_key = ArtifactKey(
        artifact_id=ArtifactId(f"{job.output.artifact_id.value}:split_manifest"),
        kind=ArtifactKind.SPLIT_MANIFEST,
    )
    readiness_key = ArtifactKey(
        artifact_id=ArtifactId(f"{job.output.artifact_id.value}:readiness"),
        kind=ArtifactKind.DATASET_READINESS,
    )
    preprocessing_key = ArtifactKey(
        artifact_id=ArtifactId(f"{job.output.artifact_id.value}:preprocessing"),
        kind=ArtifactKind.PREPROCESSING_EVIDENCE,
    )
    assert repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=preprocessing_key,
                artifact_format=ArtifactFormat.JSON,
                scientific_fingerprint=app.config.scientific_fingerprint,
                execution_fingerprint=app.config.execution_fingerprint,
                relative_path=preprocessing_relative_path,
                parents=(
                    ArtifactParent(
                        parent_key=job.output,
                        parent_relative_path=relative_path,
                        scientific_fingerprint=app.config.scientific_fingerprint,
                        execution_fingerprint=app.config.execution_fingerprint,
                    ),
                ),
                schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
                creation_timestamp=1.0,
                environment_identity="test",
                source_inventory_fingerprint=source_fingerprint,
            ),
            payload=BytesPayload(payload_bytes=b"preprocessing"),
        )
    ).success
    assert repository.commit(
        ArtifactCommitRequest(
            metadata=ArtifactCommitMetadata(
                artifact_key=readiness_key,
                artifact_format=ArtifactFormat.JSON,
                scientific_fingerprint=app.config.scientific_fingerprint,
                execution_fingerprint=app.config.execution_fingerprint,
                relative_path=readiness_relative_path,
                parents=(
                    ArtifactParent(
                        parent_key=job.output,
                        parent_relative_path=relative_path,
                        scientific_fingerprint=app.config.scientific_fingerprint,
                        execution_fingerprint=app.config.execution_fingerprint,
                    ),
                ),
                schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
                creation_timestamp=1.0,
                environment_identity="test",
                source_inventory_fingerprint=source_fingerprint,
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
                    ArtifactParent(
                        parent_key=job.output,
                        parent_relative_path=relative_path,
                        scientific_fingerprint=app.config.scientific_fingerprint,
                        execution_fingerprint=app.config.execution_fingerprint,
                    ),
                ),
                schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
                creation_timestamp=1.0,
                environment_identity="test",
                source_inventory_fingerprint=source_fingerprint,
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
                schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
                creation_timestamp=1.0,
                environment_identity="test",
                source_inventory_fingerprint=source_fingerprint,
            ),
            payload=BytesPayload(payload_bytes=b"already materialized"),
        )
    ).success
    outcome = DatasetMaterializationStageHandler(app.config, repository, _build_adapter_registry()).execute(job, run_id)
    assert outcome.status is JobExecutionStatus.REUSED
    assert outcome.produced_artifact == job.output
