import json

import pytest

from datp_core.domain.datasets import DatasetId
from datp_core.domain.partitions import SplitRole
from datp_core.domain.regimes import Regime
from datp_core.experiments.artifacts import write_manifest
from datp_core.experiments.overwrite_guard import (
    OverwriteGuardError,
    WriteMode,
    guard_artifact_write,
)
from datp_core.experiments.provenance import ArtifactCommon, ArtifactStatus, ScoreManifest


def _score_manifest(manifest_id: str) -> ScoreManifest:
    return ScoreManifest(
        manifest_id=manifest_id,
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        checkpoint_manifest_id="ckpt-1",
        split_role=SplitRole.CALIBRATION,
        common=ArtifactCommon(
            artifact_path="outputs/scores/score-1.json",
            created_at="2026-07-09T00:00:00Z",
            code_version="phase1-dev",
            status=ArtifactStatus.COMPLETE,
        ),
    )


def test_writing_a_manifest_twice_without_resume_mode_is_rejected(tmp_path):
    path = tmp_path / "score-1.json"
    manifest = _score_manifest("score-1")
    guard_artifact_write(path, WriteMode.CREATE_NEW)
    write_manifest(manifest, path)

    with pytest.raises(OverwriteGuardError):
        guard_artifact_write(path, WriteMode.CREATE_NEW)


def test_resuming_the_same_run_reuses_the_existing_manifest(tmp_path):
    path = tmp_path / "score-1.json"
    manifest = _score_manifest("score-1")
    write_manifest(manifest, path)

    existing_id = json.loads(path.read_text())["manifest_id"]
    guard_artifact_write(
        path,
        WriteMode.RESUME_SAME_RUN_IF_MANIFEST_MATCHES,
        existing_manifest_id=existing_id,
        requested_manifest_id="score-1",
    )

    with pytest.raises(OverwriteGuardError):
        guard_artifact_write(
            path,
            WriteMode.RESUME_SAME_RUN_IF_MANIFEST_MATCHES,
            existing_manifest_id=existing_id,
            requested_manifest_id="score-DIFFERENT",
        )
