"""Preflight execution persists the full resolved configuration immutably."""

import json
from pathlib import Path

from datp_core.app import build_application
from datp_core.artifacts.identity import ArtifactKey, ArtifactKind
from datp_core.artifacts.repository.filesystem import AtomicArtifactRepository
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.execution import PreflightStageHandler
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.enums import JobExecutionStatus, StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.node_key import StageNodeKey


def test_preflight_stage_commits_the_resolved_identity_artifact(tmp_path: Path) -> None:
    app = build_application()
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=1.0)
    ctx = StageJobContext(experiment_id=ExperimentId("anchor"))
    node_key = StageNodeKey(experiment=ExperimentId("anchor"), stage=StageKind.PREFLIGHT)
    job = StageJob(
        node_key=node_key,
        stage=StageKind.PREFLIGHT,
        context=ctx,
        inputs=(),
        output=ArtifactKey(node_key=node_key, kind=ArtifactKind.RESOLVED_CONFIG),
        dependencies=(),
    )
    outcome = PreflightStageHandler(app.config, repository).execute(job)
    assert outcome.status is JobExecutionStatus.SUCCESS
    assert outcome.produced_artifact == job.output
    stored = repository.read("experiments/anchor/preflight")
    assert stored.found
    assert stored.payload_bytes is not None
    persisted = json.loads(stored.payload_bytes)
    assert persisted["scientific_fingerprint"] == app.config.scientific_fingerprint.value
    assert persisted["execution_fingerprint"] == app.config.execution_fingerprint.value
    assert persisted["scientific_projection"] == app.config.scientific_projection
    assert persisted["execution_projection"] == app.config.execution_projection
