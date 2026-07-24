"""Simple frozen records for scoring requests and selected checkpoint metadata."""

from __future__ import annotations

from attrs import define, field


@define(frozen=True, slots=True, kw_only=True)
class ScoringRequest:
    """Parameters needed to score one materialized split against a model checkpoint."""

    split: str
    feature_columns: tuple[str, ...]
    batch_size: int
    device: str


@define(frozen=True, slots=True, kw_only=True)
class SelectedCheckpoint:
    """Reference to a single selected model checkpoint for scoring."""

    artifact_id: str
    selected_round: int
    input_dimension: int
    hidden_dims: tuple[int, ...]
    is_personalized: bool = field(default=False)
    client_ids: tuple[str, ...] = field(default=())
