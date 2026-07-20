"""Dataset materialization resumes only from the matching immutable artifact."""

from pathlib import Path

from datp_core.application.experiment_planning import PlanExperimentUseCase
from datp_core.application.stage_handlers import DatasetMaterializationStageHandler
from datp_core.composition.root import build_application
from datp_core.domain.artifacts import ArtifactCommitRequest, ArtifactFormat
from datp_core.domain.identifiers import ExperimentId, RunId
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
    assert repository.commit(
        ArtifactCommitRequest(
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            scientific_fingerprint=app.config.scientific_fingerprint,
            execution_fingerprint=app.config.execution_fingerprint,
            payload_bytes=b"already materialized",
            relative_path=relative_path,
            parents=(),
            schema_version=1,
            creation_timestamp=1.0,
            environment_identity="test",
        )
    ).success
    outcome = DatasetMaterializationStageHandler(app.config, repository).execute(job, run_id)
    assert outcome.status is JobExecutionStatus.REUSED
    assert outcome.produced_artifact == job.output
