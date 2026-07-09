import json

import pytest

from datp_core.domain.datasets import DatasetId
from datp_core.domain.metrics import Metric
from datp_core.domain.partitions import SplitRole
from datp_core.domain.policies import ThresholdPolicy, TrainingAlgorithm
from datp_core.domain.regimes import Regime
from datp_core.experiments.artifacts import (
    ManifestReuseError,
    checkpoint_manifest_from_dict,
    manifest_to_dict,
    manifest_to_json,
    metric_manifest_from_dict,
    read_manifest,
    score_manifest_from_dict,
    threshold_manifest_from_dict,
    verify_checkpoint_manifest_reuse,
    verify_score_manifest_reuse,
    write_manifest,
)
from datp_core.experiments.provenance import (
    ArtifactCommon,
    ArtifactStatus,
    CheckpointManifest,
    MetricManifest,
    RunManifest,
    RunStage,
    ScoreManifest,
    ThresholdManifest,
)

COMMON = ArtifactCommon(
    artifact_path="outputs/scores/run-1.json",
    created_at="2026-07-09T00:00:00Z",
    code_version="phase1-dev",
    status=ArtifactStatus.COMPLETE,
)


def _checkpoint() -> CheckpointManifest:
    return CheckpointManifest(
        manifest_id="ckpt-1",
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        training_algorithm=TrainingAlgorithm.FEDAVG,
        selected_round=10,
        checkpoint_selection_rule="best_benign_val_loss",
        weight_hash="abc123",
        split_manifest_id="split-1",
        common=COMMON,
    )


def test_checkpoint_manifest_round_trips_through_json(tmp_path):
    checkpoint = _checkpoint()
    path = tmp_path / "checkpoint.json"
    write_manifest(checkpoint, path)
    restored = checkpoint_manifest_from_dict(json.loads(path.read_text()))
    assert restored == checkpoint


def test_read_manifest_round_trips(tmp_path):
    checkpoint = _checkpoint()
    path = tmp_path / "checkpoint.json"
    write_manifest(checkpoint, path)
    restored = read_manifest(path, CheckpointManifest)
    assert restored == checkpoint


def test_manifest_to_json_is_valid_json():
    checkpoint = _checkpoint()
    parsed = json.loads(manifest_to_json(checkpoint))
    assert parsed["manifest_id"] == "ckpt-1"


def test_score_manifest_cannot_omit_checkpoint_id():
    with pytest.raises(ValueError):
        ScoreManifest(
            manifest_id="score-1",
            dataset_id=DatasetId.N_BAIOT,
            regime=Regime.A,
            seed=0,
            checkpoint_manifest_id="",
            split_role=SplitRole.CALIBRATION,
            common=COMMON,
        )


def test_threshold_manifest_cannot_omit_score_manifest_id():
    with pytest.raises(ValueError):
        ThresholdManifest(
            manifest_id="thr-1",
            policy=ThresholdPolicy.B1,
            dataset_id=DatasetId.N_BAIOT,
            regime=Regime.A,
            seed=0,
            score_manifest_id="",
            config_hash="cfg-hash",
            common=COMMON,
        )


def test_metric_manifest_cannot_omit_threshold_id():
    with pytest.raises(ValueError):
        MetricManifest(
            manifest_id="metric-1",
            metric=Metric.CV_FPR,
            dataset_id=DatasetId.N_BAIOT,
            regime=Regime.A,
            seed=0,
            threshold_manifest_id="",
            common=COMMON,
        )


def test_run_manifest_links_config_snapshot():
    with pytest.raises(ValueError):
        RunManifest(
            manifest_id="run-1",
            stage_name=RunStage.SCORING,
            config_snapshot_id="",
            inputs=(),
            outputs=(),
            common=COMMON,
        )
    run = RunManifest(
        manifest_id="run-1",
        stage_name=RunStage.SCORING,
        config_snapshot_id="cfg-snap-1",
        inputs=("split-1",),
        outputs=("score-1",),
        common=COMMON,
    )
    assert run.config_snapshot_id == "cfg-snap-1"


def test_verify_score_manifest_reuse_accepts_matching_identity():
    score = ScoreManifest(
        manifest_id="score-1",
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        checkpoint_manifest_id="ckpt-1",
        split_role=SplitRole.CALIBRATION,
        common=COMMON,
    )
    verify_score_manifest_reuse(score, DatasetId.N_BAIOT, Regime.A, 0, "ckpt-1")


def test_verify_score_manifest_reuse_rejects_identity_mismatch():
    score = ScoreManifest(
        manifest_id="score-1",
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        checkpoint_manifest_id="ckpt-1",
        split_role=SplitRole.CALIBRATION,
        common=COMMON,
    )
    with pytest.raises(ManifestReuseError):
        verify_score_manifest_reuse(score, DatasetId.N_BAIOT, Regime.A, 0, "ckpt-DIFFERENT")


def test_verify_checkpoint_manifest_reuse_rejects_seed_mismatch():
    checkpoint = _checkpoint()
    verify_checkpoint_manifest_reuse(checkpoint, DatasetId.N_BAIOT, Regime.A, 0, None)
    with pytest.raises(ManifestReuseError):
        verify_checkpoint_manifest_reuse(checkpoint, DatasetId.N_BAIOT, Regime.A, 1, None)


def test_manifest_to_dict_is_json_serializable():
    data = manifest_to_dict(_checkpoint())
    json.dumps(data)  # must not raise


def test_score_manifest_round_trips_through_json():
    score = ScoreManifest(
        manifest_id="score-1",
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        checkpoint_manifest_id="ckpt-1",
        split_role=SplitRole.CALIBRATION,
        common=COMMON,
    )
    restored = score_manifest_from_dict(json.loads(manifest_to_json(score)))
    assert restored == score


def test_threshold_manifest_round_trips_through_json():
    threshold = ThresholdManifest(
        manifest_id="thr-1",
        policy=ThresholdPolicy.B2,
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        score_manifest_id="score-1",
        config_hash="cfg-hash",
        common=COMMON,
    )
    restored = threshold_manifest_from_dict(json.loads(manifest_to_json(threshold)))
    assert restored == threshold


def test_metric_manifest_round_trips_through_json():
    metric = MetricManifest(
        manifest_id="metric-1",
        metric=Metric.CV_FPR,
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        threshold_manifest_id="thr-1",
        common=COMMON,
    )
    restored = metric_manifest_from_dict(json.loads(manifest_to_json(metric)))
    assert restored == metric
