"""Optimizer and batching contracts — pure resolved optimizer and batching configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.core.numbers import NonNegativeFloat, PositiveFloat, PositiveInt


class OptimizerRecord(BaseModel):
    """Pure resolved optimizer contract."""

    model_config = ConfigDict(frozen=True)

    identifier: str
    optimizer_type: str
    learning_rate: PositiveFloat
    beta_1: float
    beta_2: float
    epsilon: PositiveFloat
    weight_decay: NonNegativeFloat
    amsgrad: bool
    scheduler: str
    gradient_clipping: str
    state_lifecycle: str
    state_aggregated_by_server: bool


class BatchingRecord(BaseModel):
    """Pure resolved batching contract."""

    model_config = ConfigDict(frozen=True)

    identifier: str
    micro_batch_size: PositiveInt
    gradient_accumulation_steps: PositiveInt
    effective_batch_size: PositiveInt
    shuffle_each_epoch: bool
    shuffle_unit: str
    incomplete_final_batch: str
    row_ordering_before_shuffle: str
    shuffle_seed_namespace: str
    worker_seed_namespace: str
