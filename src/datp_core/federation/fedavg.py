"""Deterministic full-participation FedAvg for benign Regime A training."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp_core.data.splits import RegimeASplits
from datp_core.models.autoencoder import Autoencoder, ModelParameter


class FedAvgError(ValueError):
    """Raised when an anchor FedAvg configuration violates its fixed contract."""


@dataclass(frozen=True)
class FedAvgConfig:
    rounds: int
    local_epochs: int
    learning_rate: float
    momentum: float
    weight_decay: float
    full_participation: bool

    def __post_init__(self) -> None:
        if self.rounds < 1 or self.local_epochs != 1 or self.learning_rate <= 0.0:
            raise FedAvgError("anchor FedAvg requires rounds >= 1, local_epochs == 1, and positive learning_rate")
        if self.momentum < 0.0 or self.weight_decay < 0.0:
            raise FedAvgError("anchor FedAvg optimizer settings must be non-negative")
        if not self.full_participation:
            raise FedAvgError("anchor FedAvg requires full client participation")


@dataclass(frozen=True)
class TrainingRound:
    round_number: int
    mean_client_loss: float
    participating_clients: tuple[str, ...]


@dataclass(frozen=True)
class FedAvgTrainingResult:
    model: Autoencoder
    rounds: tuple[TrainingRound, ...]


def _aggregate(models: tuple[Autoencoder, ...], sample_counts: tuple[int, ...]) -> tuple[ModelParameter, ...]:
    total = sum(sample_counts)
    if total == 0:
        raise FedAvgError("FedAvg cannot aggregate empty client training datasets")
    aggregated: list[ModelParameter] = []
    for reference in models[0].numpy_parameters():
        value = np.zeros_like(reference.values)
        for model, count in zip(models, sample_counts, strict=True):
            value += model.parameter_values(reference.name) * count
        aggregated.append(ModelParameter(name=reference.name, values=value / total))
    return tuple(aggregated)


def train_fedavg_anchor(model: Autoencoder, splits: RegimeASplits, config: FedAvgConfig) -> FedAvgTrainingResult:
    """Train from held-out benign train data only; calibration and attack rows are inaccessible."""
    current = model.copy()
    records: list[TrainingRound] = []
    for round_number in range(1, config.rounds + 1):
        local_models: list[Autoencoder] = []
        sample_counts: list[int] = []
        losses: list[float] = []
        for client in splits.clients:
            local_model = current.copy()
            losses.append(
                local_model.train_epoch(
                    client.train.features,
                    learning_rate=config.learning_rate,
                    momentum=config.momentum,
                    weight_decay=config.weight_decay,
                )
            )
            local_models.append(local_model)
            sample_counts.append(len(client.train.sample_ids))
        current.load_numpy_parameters(_aggregate(tuple(local_models), tuple(sample_counts)))
        records.append(
            TrainingRound(
                round_number=round_number,
                mean_client_loss=float(np.mean(losses)),
                participating_clients=tuple(client.client_id for client in splits.clients),
            )
        )
    return FedAvgTrainingResult(model=current, rounds=tuple(records))
