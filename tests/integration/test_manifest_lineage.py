"""End-to-end manifest lineage: dataset -> preprocessing -> split -> checkpoint ->
score -> threshold -> metric, each referencing its upstream manifest_id, with
reuse-identity mismatches rejected across the whole chain."""

from typing import Any

import pytest

from datp_core.domain.datasets import DatasetId
from datp_core.domain.metrics import Metric
from datp_core.domain.partitions import SplitRole, SplitType
from datp_core.domain.policies import ThresholdPolicy, TrainingAlgorithm
from datp_core.domain.regimes import Regime
from datp_core.experiments.artifacts import (
    ManifestReuseError,
    verify_checkpoint_manifest_reuse,
    verify_score_manifest_reuse,
)
from datp_core.experiments.provenance import (
    ArtifactCommon,
    ArtifactStatus,
    CheckpointManifest,
    MetricManifest,
    PreprocessingManifest,
    ScoreManifest,
    SplitManifest,
    ThresholdManifest,
)

COMMON = ArtifactCommon(
    artifact_path="outputs/lineage/fixture.json",
    created_at="2026-07-09T00:00:00Z",
    code_version="phase1-dev",
    status=ArtifactStatus.COMPLETE,
)


def _build_chain() -> dict[str, Any]:
    preprocessing = PreprocessingManifest(
        manifest_id="preprocessing-1",
        dataset_id=DatasetId.N_BAIOT,
        preprocessing_contract_version="v1",
        raw_dataset_manifest_id="dataset-1",
        common=COMMON,
    )
    split = SplitManifest(
        manifest_id="split-1",
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        split_policy=SplitType.CHRONOLOGICAL_GAPPED,
        seed=0,
        preprocessing_manifest_id=preprocessing.manifest_id,
        common=COMMON,
    )
    checkpoint = CheckpointManifest(
        manifest_id="checkpoint-1",
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        training_algorithm=TrainingAlgorithm.FEDAVG,
        selected_round=10,
        checkpoint_selection_rule="best_benign_val_loss",
        weight_hash="hash-1",
        split_manifest_id=split.manifest_id,
        common=COMMON,
    )
    score = ScoreManifest(
        manifest_id="score-1",
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        checkpoint_manifest_id=checkpoint.manifest_id,
        split_role=SplitRole.CALIBRATION,
        common=COMMON,
    )
    threshold = ThresholdManifest(
        manifest_id="threshold-1",
        policy=ThresholdPolicy.B2,
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        score_manifest_id=score.manifest_id,
        config_hash="cfg-1",
        common=COMMON,
    )
    metric = MetricManifest(
        manifest_id="metric-1",
        metric=Metric.CV_FPR,
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        threshold_manifest_id=threshold.manifest_id,
        common=COMMON,
    )
    return {
        "preprocessing": preprocessing,
        "split": split,
        "checkpoint": checkpoint,
        "score": score,
        "threshold": threshold,
        "metric": metric,
    }


def test_lineage_chain_links_every_stage_by_manifest_id():
    chain = _build_chain()
    assert chain["split"].preprocessing_manifest_id == chain["preprocessing"].manifest_id
    assert chain["checkpoint"].split_manifest_id == chain["split"].manifest_id
    assert chain["score"].checkpoint_manifest_id == chain["checkpoint"].manifest_id
    assert chain["threshold"].score_manifest_id == chain["score"].manifest_id
    assert chain["metric"].threshold_manifest_id == chain["threshold"].manifest_id


def test_lineage_reuse_succeeds_when_identity_matches():
    chain = _build_chain()
    verify_checkpoint_manifest_reuse(chain["checkpoint"], DatasetId.N_BAIOT, Regime.A, 0, None)
    verify_score_manifest_reuse(
        chain["score"], DatasetId.N_BAIOT, Regime.A, 0, chain["checkpoint"].manifest_id
    )


def test_lineage_reuse_rejects_a_different_seed_anywhere_in_the_chain():
    chain = _build_chain()
    with pytest.raises(ManifestReuseError):
        verify_checkpoint_manifest_reuse(chain["checkpoint"], DatasetId.N_BAIOT, Regime.A, 1, None)
    with pytest.raises(ManifestReuseError):
        verify_score_manifest_reuse(
            chain["score"], DatasetId.N_BAIOT, Regime.A, 1, chain["checkpoint"].manifest_id
        )


def test_lineage_reuse_rejects_a_swapped_checkpoint():
    chain = _build_chain()
    with pytest.raises(ManifestReuseError):
        verify_score_manifest_reuse(
            chain["score"], DatasetId.N_BAIOT, Regime.A, 0, "some-other-checkpoint"
        )
