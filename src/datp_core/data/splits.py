"""Leakage-checked Regime A splits for benign training, calibration, and evaluation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from datp_core.data.nbaiot import DeviceSamples, NbaiotDataset, SampleSource
from datp_core.domain.datasets import DatasetId
from datp_core.domain.partitions import CALIBRATION_MIN_ELIGIBLE_ROWS, CHRONOLOGICAL_GAP_FRACTION, SplitType
from datp_core.domain.regimes import Regime
from datp_core.experiments.artifacts import write_manifest


class SplitError(ValueError):
    """Raised when a requested anchor split violates the benign-only contract."""


@dataclass(frozen=True)
class AnchorSplitSettings:
    split_type: SplitType
    train_fraction: float
    calibration_fraction: float
    gap_fraction: float
    seed: int


@dataclass(frozen=True)
class SplitSamples:
    sample_ids: tuple[str, ...]
    features: np.ndarray
    source: SampleSource

    def __post_init__(self) -> None:
        if self.features.ndim != 2 or len(self.sample_ids) != self.features.shape[0]:
            raise SplitError("split sample IDs and feature rows must have matching two-dimensional shapes")
        self.features.setflags(write=False)


@dataclass(frozen=True)
class ClientSplit:
    client_id: str
    train: SplitSamples
    calibration: SplitSamples
    test_benign: SplitSamples
    test_attack: SplitSamples
    calibration_eligible: bool

    def __post_init__(self) -> None:
        if self.train.source is not SampleSource.BENIGN or self.calibration.source is not SampleSource.BENIGN:
            raise SplitError("training and calibration samples must be benign")
        if self.test_benign.source is not SampleSource.BENIGN or self.test_attack.source is not SampleSource.ATTACK:
            raise SplitError("test sources must be held-out benign and attack respectively")
        ids = self.train.sample_ids + self.calibration.sample_ids + self.test_benign.sample_ids
        if len(set(ids)) != len(ids):
            raise SplitError(f"benign split overlap detected for client {self.client_id}")
        if set(self.test_attack.sample_ids) & set(ids):
            raise SplitError(f"attack samples overlap a benign split for client {self.client_id}")
        if self.calibration_eligible != (len(self.calibration.sample_ids) >= CALIBRATION_MIN_ELIGIBLE_ROWS):
            raise SplitError("calibration eligibility must follow the locked n_min threshold")


@dataclass(frozen=True)
class RegimeASplits:
    seed: int
    clients: tuple[ClientSplit, ...]
    split_config_hash: str
    split_type: SplitType

    def __post_init__(self) -> None:
        client_ids = tuple(client.client_id for client in self.clients)
        if len(client_ids) != len(set(client_ids)):
            raise SplitError("split client IDs must be unique")
        if not self.clients:
            raise SplitError("Regime A split requires at least one client")


@dataclass(frozen=True)
class SplitManifestEntry:
    client_id: str
    calibration_eligible: bool
    train_ids: tuple[str, ...]
    calibration_ids: tuple[str, ...]
    test_benign_ids: tuple[str, ...]
    test_attack_ids: tuple[str, ...]


@dataclass(frozen=True)
class AnchorSplitManifest:
    dataset_id: DatasetId
    regime_id: Regime
    seed: int
    split_type: SplitType
    split_config_hash: str
    clients: tuple[SplitManifestEntry, ...]


def _slice(samples: DeviceSamples, start: int, stop: int) -> SplitSamples:
    return SplitSamples(
        sample_ids=samples.sample_ids[start:stop],
        features=samples.features[start:stop].copy(),
        source=samples.source,
    )


def build_regime_a_splits(
    dataset: NbaiotDataset,
    *,
    seed: int,
    train_fraction: float,
    calibration_fraction: float,
) -> RegimeASplits:
    """Build chronological benign partitions with locked 1% buffer gaps and preserve every attack row.

    docs/protocol/artifact_contracts.md #1.1: 60% train / 1% gap / 20% calibration / 1% gap / 18% test,
    per device, original row order preserved. The gap rows are excluded from every partition.
    """
    if not (0.0 < train_fraction < 1.0 and 0.0 < calibration_fraction < 1.0):
        raise SplitError("split fractions must be strictly between zero and one")
    if train_fraction + calibration_fraction + 2 * CHRONOLOGICAL_GAP_FRACTION >= 1.0:
        raise SplitError("train, calibration, and gap fractions must leave held-out benign test rows")
    clients: list[ClientSplit] = []
    for device_id in dataset.device_ids:
        benign = dataset.by_device(device_id, SampleSource.BENIGN)
        attack = dataset.by_device(device_id, SampleSource.ATTACK)
        row_count = len(benign.sample_ids)
        train_end = int(row_count * train_fraction)
        calibration_start = train_end + int(row_count * CHRONOLOGICAL_GAP_FRACTION)
        calibration_end = calibration_start + int(row_count * calibration_fraction)
        test_start = calibration_end + int(row_count * CHRONOLOGICAL_GAP_FRACTION)
        if train_end == 0 or calibration_end == calibration_start or test_start >= row_count:
            raise SplitError(f"insufficient benign rows to build all splits for client {device_id}")
        calibration = _slice(benign, calibration_start, calibration_end)
        clients.append(
            ClientSplit(
                client_id=device_id,
                train=_slice(benign, 0, train_end),
                calibration=calibration,
                test_benign=_slice(benign, test_start, row_count),
                test_attack=SplitSamples(
                    sample_ids=attack.sample_ids,
                    features=attack.features.copy(),
                    source=SampleSource.ATTACK,
                ),
                calibration_eligible=len(calibration.sample_ids) >= CALIBRATION_MIN_ELIGIBLE_ROWS,
            )
        )
    split_settings = AnchorSplitSettings(
        split_type=SplitType.CHRONOLOGICAL_GAPPED,
        train_fraction=train_fraction,
        calibration_fraction=calibration_fraction,
        gap_fraction=CHRONOLOGICAL_GAP_FRACTION,
        seed=seed,
    )
    config_hash = hashlib.sha256(json.dumps(asdict(split_settings), default=str, sort_keys=True).encode()).hexdigest()
    return RegimeASplits(
        seed=seed,
        clients=tuple(clients),
        split_config_hash=config_hash,
        split_type=split_settings.split_type,
    )


def validate_regime_a_splits(splits: RegimeASplits) -> None:
    """Re-run the complete leakage and identity checks before heavy stages."""
    for client in splits.clients:
        ClientSplit(
            client_id=client.client_id,
            train=client.train,
            calibration=client.calibration,
            test_benign=client.test_benign,
            test_attack=client.test_attack,
            calibration_eligible=client.calibration_eligible,
        )


def write_split_manifest(
    splits: RegimeASplits,
    path: Path,
    *,
    dataset_id: DatasetId,
    regime: Regime,
) -> None:
    write_manifest(
        AnchorSplitManifest(
            dataset_id=dataset_id,
            regime_id=regime,
            seed=splits.seed,
            split_type=splits.split_type,
            split_config_hash=splits.split_config_hash,
            clients=tuple(
                SplitManifestEntry(
                    client_id=client.client_id,
                    calibration_eligible=client.calibration_eligible,
                    train_ids=client.train.sample_ids,
                    calibration_ids=client.calibration.sample_ids,
                    test_benign_ids=client.test_benign.sample_ids,
                    test_attack_ids=client.test_attack.sample_ids,
                )
                for client in splits.clients
            ),
        ),
        path,
    )
