import json

import numpy as np
import pytest

from datp_core.data.nbaiot import SampleSource
from datp_core.data.preprocessing import fit_feature_scaler, transform_regime_a_splits
from datp_core.data.splits import SplitError, build_regime_a_splits, validate_regime_a_splits, write_split_manifest
from datp_core.domain.datasets import DatasetId
from datp_core.domain.partitions import SplitType
from datp_core.domain.regimes import Regime
from datp_core.evaluation.classification import ClientMetrics
from datp_core.evaluation.disparity import MetricError, compute_fpr_disparity
from datp_core.experiments.anchor import FixtureDataConfig, fixture_nbaiot_dataset
from datp_core.experiments.plan import AnchorPlanError, confirmatory_anchor_plan
from datp_core.federation.fedavg import FedAvgConfig, FedAvgError, train_fedavg_anchor
from datp_core.models.autoencoder import Autoencoder
from datp_core.partitioning.physical_device import PhysicalDeviceMappingError, build_physical_device_client_map
from datp_core.utils.hardware import DeviceType

_FIXTURE_CLIENT_COUNT = 2
_FIXTURE_BENIGN_ROWS = 520
_FIXTURE_ATTACK_ROWS = 80
_TRAIN_FRACTION = 0.6
_CALIBRATION_FRACTION = 0.2
_TEST_SEED = 0
_TEST_HIDDEN_DIM = 4
_TEST_LEARNING_RATE = 0.01
_TEST_MOMENTUM = 0.0
_TEST_WEIGHT_DECAY = 0.0
_FIXTURE_CONFIG = FixtureDataConfig(
    fixture_client_count=_FIXTURE_CLIENT_COUNT,
    benign_rows=_FIXTURE_BENIGN_ROWS,
    attack_rows=_FIXTURE_ATTACK_ROWS,
    feature_count=3,
    benign_mean_step=0.2,
    attack_mean=3.0,
    feature_std=0.25,
)


def test_physical_mapping_and_splits_are_leakage_checked(tmp_path):
    dataset = fixture_nbaiot_dataset(_FIXTURE_CONFIG)
    mapping = build_physical_device_client_map(dataset.device_ids, expected_client_count=_FIXTURE_CLIENT_COUNT)
    splits = build_regime_a_splits(
        dataset,
        seed=_TEST_SEED,
        train_fraction=_TRAIN_FRACTION,
        calibration_fraction=_CALIBRATION_FRACTION,
    )
    validate_regime_a_splits(splits)
    assert mapping.client_ids == tuple(sorted(dataset.device_ids))
    assert all(client.calibration_eligible for client in splits.clients)
    manifest_path = tmp_path / "split.json"
    write_split_manifest(splits, manifest_path, dataset_id=DatasetId.N_BAIOT, regime=Regime.A)
    assert len(json.loads(manifest_path.read_text())["clients"]) == 2
    with pytest.raises(PhysicalDeviceMappingError):
        build_physical_device_client_map(("only-one",), expected_client_count=_FIXTURE_CLIENT_COUNT)
    duplicate = splits.clients[0]
    with pytest.raises(SplitError):
        type(duplicate)(
            client_id=duplicate.client_id,
            train=duplicate.train,
            calibration=duplicate.train,
            test_benign=duplicate.test_benign,
            test_attack=duplicate.test_attack,
            calibration_eligible=duplicate.calibration_eligible,
        )


def test_chronological_split_leaves_locked_one_percent_gaps_between_partitions():
    """docs/protocol/artifact_contracts.md #1.1: 60% train / 1% gap / 20% calibration / 1% gap / 18% test."""
    dataset = fixture_nbaiot_dataset(_FIXTURE_CONFIG)
    splits = build_regime_a_splits(
        dataset,
        seed=_TEST_SEED,
        train_fraction=_TRAIN_FRACTION,
        calibration_fraction=_CALIBRATION_FRACTION,
    )
    assert splits.split_type is SplitType.CHRONOLOGICAL_GAPPED
    client = splits.clients[0]
    gap_rows = int(_FIXTURE_BENIGN_ROWS * 0.01)
    assert len(client.train.sample_ids) == int(_FIXTURE_BENIGN_ROWS * _TRAIN_FRACTION)
    assert len(client.calibration.sample_ids) == int(_FIXTURE_BENIGN_ROWS * _CALIBRATION_FRACTION)
    assert (
        len(client.test_benign.sample_ids)
        == _FIXTURE_BENIGN_ROWS
        - int(_FIXTURE_BENIGN_ROWS * _TRAIN_FRACTION)
        - int(_FIXTURE_BENIGN_ROWS * _CALIBRATION_FRACTION)
        - 2 * gap_rows
    )
    kept = len(client.train.sample_ids) + len(client.calibration.sample_ids) + len(client.test_benign.sample_ids)
    assert kept == _FIXTURE_BENIGN_ROWS - 2 * gap_rows
    all_ids = set(client.train.sample_ids) | set(client.calibration.sample_ids) | set(client.test_benign.sample_ids)
    dataset_benign_ids = set(dataset.by_device(client.client_id, SampleSource.BENIGN).sample_ids)
    assert dataset_benign_ids - all_ids  # the gap rows are excluded from every split


def test_autoencoder_and_fedavg_train_on_benign_train_only():
    dataset = fixture_nbaiot_dataset(_FIXTURE_CONFIG)
    splits = transform_regime_a_splits(
        build_regime_a_splits(
            dataset,
            seed=_TEST_SEED,
            train_fraction=_TRAIN_FRACTION,
            calibration_fraction=_CALIBRATION_FRACTION,
        ),
        fit_feature_scaler(
            build_regime_a_splits(
                dataset,
                seed=_TEST_SEED,
                train_fraction=_TRAIN_FRACTION,
                calibration_fraction=_CALIBRATION_FRACTION,
            )
        ),
    )
    model = Autoencoder.initialize(3, seed=7, hidden_dim=_TEST_HIDDEN_DIM, device=DeviceType.CUDA)
    before = model.parameter_values("0.weight")
    result = train_fedavg_anchor(
        model,
        splits,
        FedAvgConfig(
            rounds=1,
            local_epochs=1,
            learning_rate=_TEST_LEARNING_RATE,
            momentum=_TEST_MOMENTUM,
            weight_decay=_TEST_WEIGHT_DECAY,
            full_participation=True,
        ),
    )
    assert result.rounds[0].participating_clients == tuple(client.client_id for client in splits.clients)
    assert not np.array_equal(before, result.model.parameter_values("0.weight"))
    with pytest.raises(FedAvgError):
        FedAvgConfig(
            rounds=1,
            local_epochs=2,
            learning_rate=_TEST_LEARNING_RATE,
            momentum=_TEST_MOMENTUM,
            weight_decay=_TEST_WEIGHT_DECAY,
            full_participation=True,
        )


def test_metrics_and_confirmatory_plan_contracts():
    metrics = (
        ClientMetrics("a", 0.1, 0.8, 0.85, 0.8, 0.9),
        ClientMetrics("b", 0.2, 0.9, 0.85, 0.8, 0.9),
    )
    assert compute_fpr_disparity(metrics).worst_client_fpr == 0.2
    with pytest.raises(MetricError):
        compute_fpr_disparity((metrics[0],))
    with pytest.raises(MetricError):
        ClientMetrics("a", -0.1, 0.8, 0.85, 0.8, 0.9)
    plan = confirmatory_anchor_plan(seeds=tuple(range(10)), q=0.95)
    assert len(plan) == 20
    assert {cell.policy.value for cell in plan} == {"B1", "B2"}
    with pytest.raises(AnchorPlanError):
        confirmatory_anchor_plan(seeds=(0, 1), q=0.95)
