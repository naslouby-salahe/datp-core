"""Checkpoint contracts — pure resolved checkpoint convergence, selection, and profile records."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.core.identifiers import CheckpointProfileId
from datp_core.core.numbers import PositiveFloat, PositiveInt


class CheckpointConvergenceRecord(BaseModel):
    """Pure resolved historical convergence rule (anchor terminal-checkpoint selection)."""

    model_config = ConfigDict(frozen=True)

    metric: str
    rounds_initial: PositiveInt
    rule: str
    formula: str
    zero_start_loss_behavior: str
    tolerance: PositiveFloat
    window_rounds: PositiveInt
    window: str
    qualification: str
    no_qualifying_round_behavior: str


class CheckpointSelectionRecord(BaseModel):
    """Pure resolved checkpoint selection contract."""

    model_config = ConfigDict(frozen=True)

    rule: str
    tie_break: str | None
    scope: str | None
    aggregation: str | None
    selected_round_application_scope: str | None
    selection_granularity: str | None
    forbidden_selectors: tuple[str, ...]


class CheckpointProfileRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: CheckpointProfileId
    total_rounds: PositiveInt | None
    selected_rounds: tuple[PositiveInt, ...]
    early_stopping: str
    selection_rule: str
    selection: CheckpointSelectionRecord
    convergence: CheckpointConvergenceRecord | None
    checkpoint_save_policy: str | None
