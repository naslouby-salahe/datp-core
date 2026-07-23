"""Preflight execution persists the full resolved configuration immutably."""

import json
from pathlib import Path

from datp_core.artifacts.models import ArtifactKey, ArtifactKind
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.bootstrap import build_application
from datp_core.datasets.materialization import PreflightStageHandler
from datp_core.pipeline.identifiers import ArtifactId, ExperimentId, JobId, RunId
from datp_core.pipeline.models import JobExecutionStatus, StageJob, StageJobContext, StageKind


def test_preflight_stage_commits_the_resolved_identity_artifact(tmp_path: Path) -> None:
    app = build_application()
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    ctx = StageJobContext(experiment_id=ExperimentId("anchor"))
    job = StageJob(
        job_id=JobId("anchor:preflight"),
        stage=StageKind.PREFLIGHT,
        context=ctx,
        inputs=(),
        output=ArtifactKey(artifact_id=ArtifactId("anchor:preflight"), kind=ArtifactKind.RESOLVED_CONFIG),
        dependencies=(),
    )
    outcome = PreflightStageHandler(app.config, repository).execute(job, RunId("run_anchor"))
    assert outcome.status is JobExecutionStatus.SUCCESS
    assert outcome.produced_artifact == job.output
    stored = repository.read("runs/run_anchor/anchor:preflight")
    assert stored.found
    assert stored.payload_bytes is not None
    persisted = json.loads(stored.payload_bytes)
    assert persisted["scientific_fingerprint"] == app.config.scientific_fingerprint.value
    assert persisted["execution_fingerprint"] == app.config.execution_fingerprint.value
    assert persisted["scientific_projection"] == app.config.scientific_projection
    assert persisted["execution_projection"] == app.config.execution_projection
