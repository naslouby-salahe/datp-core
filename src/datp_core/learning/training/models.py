"""Data models for federated training results and checkpoint serialization."""

from __future__ import annotations

import torch
import torch.nn as nn
from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class FederatedCheckpoint:
    round_number: int
    state: tuple[tuple[str, torch.Tensor], ...]


@define(frozen=True, slots=True, kw_only=True)
class DataloaderShuffleSeed:
    round_number: int
    client_id: str
    local_epoch: int
    value: int


@define(frozen=True, slots=True, kw_only=True)
class FederatedTrainingResult:
    model: nn.Module
    round_losses: tuple[tuple[int, float], ...]
    scheduled_checkpoints: tuple[FederatedCheckpoint, ...]
    derived_shuffle_seeds: tuple[DataloaderShuffleSeed, ...]


@define(frozen=True, slots=True, kw_only=True)
class DittoCheckpoint:
    round_number: int
    global_state: tuple[tuple[str, torch.Tensor], ...]
    personalized_states: tuple[tuple[str, tuple[tuple[str, torch.Tensor], ...]], ...]


@define(frozen=True, slots=True, kw_only=True)
class DittoTrainingResult:
    global_model: nn.Module
    personalized_models: tuple[tuple[str, nn.Module], ...]
    global_round_losses: tuple[tuple[int, float], ...]
    personalized_round_losses: tuple[tuple[int, float], ...]
    scheduled_checkpoints: tuple[DittoCheckpoint, ...]
    derived_shuffle_seeds: tuple[DataloaderShuffleSeed, ...]
