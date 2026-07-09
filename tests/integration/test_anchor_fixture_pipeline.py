import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from datp_core.config.schemas import AnchorArtifactLayout
from datp_core.domain.datasets import DatasetId
from datp_core.domain.regimes import Regime
from datp_core.domain.seeds import SeedPlan, SeedRole
from datp_core.experiments.anchor import AnchorRuntimeConfig, AnchorSplitConfig, FixtureDataConfig, run_fixture_anchor
from datp_core.federation.fedavg import FedAvgConfig
from datp_core.models.checkpoints import read_anchor_checkpoint_manifest
from datp_core.models.frozen import load_frozen_anchor_checkpoint
from datp_core.models.scoring import ScoreArtifactError, ScoreArtifactManifest, validate_score_reuse
from datp_core.utils.hardware import DeviceType


def _runtime_config(rounds: int) -> AnchorRuntimeConfig:
    return AnchorRuntimeConfig(
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed_plan=SeedPlan(seeds=(0, 1), role=SeedRole.TRAIN),
        hidden_dim=4,
        device=DeviceType.CUDA,
        fedavg=FedAvgConfig(rounds, 1, 0.01, 0.0, 0.0, True),
        split=AnchorSplitConfig(0.6, 0.2),
        threshold_q=0.95,
        expected_client_count=9,
        fixture=FixtureDataConfig(2, 520, 80, 3, 0.2, 3.0, 0.25),
        artifacts=AnchorArtifactLayout(
            run_root_prefix="anchor",
            seed_directory_prefix="seed",
            preprocessing_id_prefix="scaler",
            client_map_filename="client-map.json",
            split_manifest_filename="split.json",
            checkpoint_filename="checkpoint.npz",
            score_filename="scores.npz",
            summary_filename="summary.json",
            threshold_filename="thresholds.json",
        ),
    )


def test_fixture_anchor_runs_two_paired_seeds_with_lineage(tmp_path):
    results = run_fixture_anchor(
        seeds=(0, 1),
        output_root=tmp_path / "outputs",
        checkpoint_root=tmp_path / "checkpoints",
        config=_runtime_config(rounds=2),
    )
    assert len(results) == 2
    for result in results:
        checkpoint = Path(result.checkpoint_path)
        manifest = read_anchor_checkpoint_manifest(checkpoint.with_suffix(".json"))
        frozen = load_frozen_anchor_checkpoint(checkpoint, manifest, device=DeviceType.CUDA)
        with pytest.raises(ValueError):
            frozen.model.train_epoch(np.zeros((2, 3)), learning_rate=0.01, momentum=0.0, weight_decay=0.0)
        summary = json.loads((Path(result.score_path).parent / "summary.json").read_text())
        assert summary["checkpoint_id"] == manifest.checkpoint_id


def test_score_reuse_and_checkpoint_mismatch_fail_loudly(tmp_path):
    results = run_fixture_anchor(
        seeds=(0,),
        output_root=tmp_path / "outputs",
        checkpoint_root=tmp_path / "checkpoints",
        config=_runtime_config(rounds=1),
    )
    manifest_path = tmp_path / "outputs" / "seed-0" / "scores.json"
    data = json.loads(manifest_path.read_text())
    existing = ScoreArtifactManifest(
        score_id=data["score_id"],
        dataset_id=data["dataset_id"],
        regime=data["regime"],
        client_mapping_id=data["client_mapping_id"],
        split_id=data["split_id"],
        preprocessing_id=data["preprocessing_id"],
        checkpoint_id=data["checkpoint_id"],
        model_architecture_id=data["model_architecture_id"],
        training_algorithm=data["training_algorithm"],
        seed=data["seed"],
        score_contract_id=data["score_contract_id"],
        client_calibration_eligibility=tuple(
            (str(client_id), bool(eligible)) for client_id, eligible in data["client_calibration_eligibility"]
        ),
    )
    requested = replace(existing, checkpoint_id="different")
    with pytest.raises(ScoreArtifactError, match="checkpoint_id"):
        validate_score_reuse(existing, requested)
    assert results[0].summary.checkpoint_id == existing.checkpoint_id
