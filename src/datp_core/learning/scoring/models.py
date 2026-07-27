"""Simple frozen records for scoring requests and selected checkpoint metadata."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScoringRequest(BaseModel):
    """Parameters needed to score one materialized split against a model checkpoint."""

    model_config = ConfigDict(frozen=True)
    split: str
    feature_columns: tuple[str, ...]
    batch_size: int
    device: str


class SelectedCheckpoint(BaseModel):
    """Reference to a single selected model checkpoint for scoring."""

    model_config = ConfigDict(frozen=True)
    artifact_id: str
    selected_round: int
    input_dimension: int
    hidden_dims: tuple[int, ...]
    is_personalized: bool = Field(default=False)
    client_ids: tuple[str, ...] = Field(default=())
