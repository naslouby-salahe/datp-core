"""Preflight execution reports success only after an artifact commit."""

from pathlib import Path

from datp_core.application.stage_handlers import PreflightStageHandler
from datp_core.composition.root import build_application
from datp_core.domain.artifacts import ArtifactKey, ArtifactKind
from datp_core.domain.identifiers import ArtifactId, JobId, RunId
from datp_core.domain.outcomes import JobExecutionStatus, StageJob, StageKind
from datp_core.infrastructure.artifacts.atomic_commit import AtomicArtifactRepository


def test_preflight_stage_commits_the_resolved_identity_artifact(tmp_path: Path) -> None:
    app = build_application()
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    job = StageJob(
        job_id=JobId("anchor:preflight"),
        stage=StageKind.PREFLIGHT,
        inputs=(),
        output=ArtifactKey(artifact_id=ArtifactId("anchor:preflight"), kind=ArtifactKind.RESOLVED_CONFIG),
        dependencies=(),
    )
    outcome = PreflightStageHandler(app.config, repository).execute(job, RunId("run_anchor"))
    assert outcome.status is JobExecutionStatus.SUCCESS
    assert outcome.produced_artifact == job.output
    assert repository.read("runs/run_anchor/anchor:preflight").found
