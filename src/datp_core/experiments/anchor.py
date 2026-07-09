"""Fixture and real-data execution wiring for the Regime A B1/B2 anchor."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from datp_core.config.schemas import AnchorArtifactLayout
from datp_core.data.nbaiot import DatasetInventory, DeviceSamples, NbaiotDataset, SampleSource, load_nbaiot
from datp_core.data.preprocessing import fit_feature_scaler, transform_regime_a_splits
from datp_core.data.splits import build_regime_a_splits, validate_regime_a_splits, write_split_manifest
from datp_core.domain.datasets import DatasetId
from datp_core.domain.regimes import Regime
from datp_core.domain.seeds import SeedPlan
from datp_core.evaluation.aggregation import AnchorSeedSummary, paired_anchor_summary
from datp_core.evaluation.classification import evaluate_client_metrics
from datp_core.evaluation.disparity import compute_fpr_disparity
from datp_core.evaluation.predictions import make_anchor_predictions
from datp_core.federation.fedavg import FedAvgConfig, train_fedavg_anchor
from datp_core.models.autoencoder import Autoencoder
from datp_core.models.checkpoints import save_anchor_checkpoint
from datp_core.models.frozen import load_frozen_anchor_checkpoint
from datp_core.models.scoring import generate_anchor_scores, write_score_artifact
from datp_core.partitioning.physical_device import build_physical_device_client_map, write_client_map_manifest
from datp_core.thresholding.local import compute_b2_local_threshold
from datp_core.thresholding.shared import compute_b1_shared_threshold
from datp_core.utils.hardware import DeviceType


@dataclass(frozen=True)
class AnchorRuntimeConfig:
    dataset_id: DatasetId
    regime: Regime
    seed_plan: SeedPlan
    hidden_dim: int
    device: DeviceType
    fedavg: FedAvgConfig
    split: AnchorSplitConfig
    threshold_q: float
    expected_client_count: int
    fixture: FixtureDataConfig
    artifacts: AnchorArtifactLayout


@dataclass(frozen=True)
class AnchorSplitConfig:
    train_fraction: float
    calibration_fraction: float


@dataclass(frozen=True)
class FixtureDataConfig:
    fixture_client_count: int
    benign_rows: int
    attack_rows: int
    feature_count: int
    benign_mean_step: float
    attack_mean: float
    feature_std: float


@dataclass(frozen=True)
class AnchorRunResult:
    summary: AnchorSeedSummary
    checkpoint_path: str
    score_path: str


def fixture_nbaiot_dataset(config: FixtureDataConfig) -> NbaiotDataset:
    """Create deterministic in-memory fixture data without creating or modifying raw data."""
    if config.fixture_client_count < 2 or config.benign_rows < 500 or config.attack_rows < 1:
        raise ValueError("fixture anchor requires at least two clients, 500 benign rows, and one attack row")
    samples: list[DeviceSamples] = []
    for client_number in range(config.fixture_client_count):
        device_id = f"fixture-device-{client_number:02d}"
        generator = np.random.default_rng(client_number)
        benign = generator.normal(
            loc=client_number * config.benign_mean_step,
            scale=config.feature_std,
            size=(config.benign_rows, config.feature_count),
        )
        attack = generator.normal(
            loc=config.attack_mean + client_number * config.benign_mean_step,
            scale=config.feature_std,
            size=(config.attack_rows, config.feature_count),
        )
        samples.extend(
            (
                DeviceSamples(
                    device_id=device_id,
                    source=SampleSource.BENIGN,
                    sample_ids=tuple(f"{device_id}:benign:{row}" for row in range(config.benign_rows)),
                    features=benign,
                ),
                DeviceSamples(
                    device_id=device_id,
                    source=SampleSource.ATTACK,
                    sample_ids=tuple(f"{device_id}:attack:{row}" for row in range(config.attack_rows)),
                    features=attack,
                ),
            )
        )
    inventory = DatasetInventory(root="fixture", files=(), unsupported_files=(), missing_devices=(), ambiguous_files=())
    return NbaiotDataset(
        feature_columns=tuple(f"f{index}" for index in range(config.feature_count)),
        samples=tuple(samples),
        inventory=inventory,
    )


def run_anchor_seed(
    dataset: NbaiotDataset,
    *,
    seed: int,
    output_root: Path,
    checkpoint_root: Path,
    config: AnchorRuntimeConfig,
    expected_client_count: int,
) -> AnchorRunResult:
    client_map = build_physical_device_client_map(dataset.device_ids, expected_client_count=expected_client_count)
    raw_splits = build_regime_a_splits(
        dataset,
        seed=seed,
        train_fraction=config.split.train_fraction,
        calibration_fraction=config.split.calibration_fraction,
    )
    validate_regime_a_splits(raw_splits)
    splits = transform_regime_a_splits(raw_splits, fit_feature_scaler(raw_splits))
    split_id = splits.split_config_hash
    seed_root = output_root / f"{config.artifacts.seed_directory_prefix}-{seed}"
    write_client_map_manifest(client_map, seed_root / config.artifacts.client_map_filename)
    write_split_manifest(
        splits,
        seed_root / config.artifacts.split_manifest_filename,
        dataset_id=config.dataset_id,
        regime=config.regime,
    )
    model = Autoencoder.initialize(
        len(dataset.feature_columns), seed=seed, hidden_dim=config.hidden_dim, device=config.device
    )
    training = train_fedavg_anchor(
        model,
        splits,
        config.fedavg,
    )
    checkpoint_path = (
        checkpoint_root / f"{config.artifacts.seed_directory_prefix}-{seed}" / config.artifacts.checkpoint_filename
    )
    checkpoint_manifest = save_anchor_checkpoint(
        training.model,
        checkpoint_path,
        dataset_id=config.dataset_id,
        regime=config.regime,
        seed=seed,
        split_id=split_id,
        selected_round=config.fedavg.rounds,
    )
    frozen = load_frozen_anchor_checkpoint(checkpoint_path, checkpoint_manifest, device=config.device)
    scores = generate_anchor_scores(
        frozen,
        splits,
        client_mapping_id="|".join(client_map.client_ids),
        preprocessing_id=f"{config.artifacts.preprocessing_id_prefix}-{split_id[:16]}",
    )
    score_path = seed_root / config.artifacts.score_filename
    write_score_artifact(scores, score_path)
    b1 = compute_b1_shared_threshold(scores, q=config.threshold_q)
    b2 = compute_b2_local_threshold(scores, q=config.threshold_q)
    b1_metrics = evaluate_client_metrics(scores, make_anchor_predictions(scores, b1))
    b2_metrics = evaluate_client_metrics(scores, make_anchor_predictions(scores, b2))
    eligible_b1_metrics = tuple(
        metric for metric, client in zip(b1_metrics, scores.clients, strict=True) if client.calibration_eligible
    )
    eligible_b2_metrics = tuple(
        metric for metric, client in zip(b2_metrics, scores.clients, strict=True) if client.calibration_eligible
    )
    summary = paired_anchor_summary(
        seed,
        checkpoint_manifest.checkpoint_id,
        checkpoint_manifest.checkpoint_id,
        compute_fpr_disparity(eligible_b1_metrics).cv_fpr,
        compute_fpr_disparity(eligible_b2_metrics).cv_fpr,
    )
    (seed_root / config.artifacts.summary_filename).write_text(json.dumps(asdict(summary), indent=2, sort_keys=True))
    return AnchorRunResult(summary=summary, checkpoint_path=str(checkpoint_path), score_path=str(score_path))


def run_fixture_anchor(
    *,
    seeds: tuple[int, ...],
    output_root: Path,
    config: AnchorRuntimeConfig,
    checkpoint_root: Path,
) -> tuple[AnchorRunResult, ...]:
    dataset = fixture_nbaiot_dataset(config.fixture)
    return tuple(
        run_anchor_seed(
            dataset,
            seed=seed,
            output_root=output_root,
            checkpoint_root=checkpoint_root,
            config=config,
            expected_client_count=config.fixture.fixture_client_count,
        )
        for seed in seeds
    )


def run_real_anchor(
    *,
    raw_root: Path,
    seeds: tuple[int, ...],
    output_root: Path,
    checkpoint_root: Path,
    config: AnchorRuntimeConfig,
) -> tuple[AnchorRunResult, ...]:
    dataset = load_nbaiot(raw_root)
    return tuple(
        run_anchor_seed(
            dataset,
            seed=seed,
            output_root=output_root,
            checkpoint_root=checkpoint_root,
            config=config,
            expected_client_count=config.expected_client_count,
        )
        for seed in seeds
    )
