"""Leakage-checked Regime A splits for benign training, calibration, and evaluation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from datp_core.data.nbaiot import DeviceSamples, NbaiotDataset, SampleSource
from datp_core.domain.datasets import DatasetId
from datp_core.domain.partitions import CALIBRATION_MIN_ELIGIBLE_ROWS, SplitType
from datp_core.domain.regimes import Regime


class SplitError(ValueError):
    """Raised when a requested anchor split violates the benign-only contract."""


@dataclass(frozen=True)
class AnchorSplitSettings:
    split_type: SplitType
    train_fraction: float
    calibration_fraction: float
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
    """Build chronological benign partitions and preserve every attack row for evaluation."""
    if not (0.0 < train_fraction < 1.0 and 0.0 < calibration_fraction < 1.0):
        raise SplitError("split fractions must be strictly between zero and one")
    if train_fraction + calibration_fraction >= 1.0:
        raise SplitError("train and calibration fractions must leave held-out benign test rows")
    clients: list[ClientSplit] = []
    for device_id in dataset.device_ids:
        benign = dataset.by_device(device_id, SampleSource.BENIGN)
        attack = dataset.by_device(device_id, SampleSource.ATTACK)
        train_end = int(len(benign.sample_ids) * train_fraction)
        calibration_end = train_end + int(len(benign.sample_ids) * calibration_fraction)
        if train_end == 0 or calibration_end == train_end or calibration_end >= len(benign.sample_ids):
            raise SplitError(f"insufficient benign rows to build all splits for client {device_id}")
        calibration = _slice(benign, train_end, calibration_end)
        clients.append(
            ClientSplit(
                client_id=device_id,
                train=_slice(benign, 0, train_end),
                calibration=calibration,
                test_benign=_slice(benign, calibration_end, len(benign.sample_ids)),
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
    document = {
        "dataset_id": dataset_id.value,
        "regime_id": regime.value,
        "seed": splits.seed,
        "split_type": splits.split_type.value,
        "split_config_hash": splits.split_config_hash,
        "clients": [
            {
                "client_id": client.client_id,
                "calibration_eligible": client.calibration_eligible,
                "train_ids": list(client.train.sample_ids),
                "calibration_ids": list(client.calibration.sample_ids),
                "test_benign_ids": list(client.test_benign.sample_ids),
                "test_attack_ids": list(client.test_attack.sample_ids),
            }
            for client in splits.clients
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True))
