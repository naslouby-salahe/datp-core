"""Data models for federated training results and checkpoint serialization."""

from __future__ import annotations

import torch
from pydantic import BaseModel, ConfigDict
from torch import nn


class FederatedCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    round_number: int
    state: tuple[tuple[str, torch.Tensor], ...]


class DataloaderShuffleSeed(BaseModel):
    model_config = ConfigDict(frozen=True)
    round_number: int
    client_id: str
    local_epoch: int
    value: int


class FederatedTrainingResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    model: nn.Module
    round_losses: tuple[tuple[int, float], ...]
    scheduled_checkpoints: tuple[FederatedCheckpoint, ...]
    derived_shuffle_seeds: tuple[DataloaderShuffleSeed, ...]


class DittoCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    round_number: int
    global_state: tuple[tuple[str, torch.Tensor], ...]
    personalized_states: tuple[tuple[str, tuple[tuple[str, torch.Tensor], ...]], ...]


class DittoTrainingResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    global_model: nn.Module
    personalized_models: tuple[tuple[str, nn.Module], ...]
    global_round_losses: tuple[tuple[int, float], ...]
    personalized_round_losses: tuple[tuple[int, float], ...]
    scheduled_checkpoints: tuple[DittoCheckpoint, ...]
    derived_shuffle_seeds: tuple[DataloaderShuffleSeed, ...]
