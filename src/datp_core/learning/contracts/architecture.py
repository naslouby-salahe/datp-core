"""Model architecture contract — pure resolved fixed-autoencoder architecture."""

from __future__ import annotations

from attrs import define

from datp_core.core.numbers import PositiveInt


@define(frozen=True, slots=True, kw_only=True)
class ModelArchitectureRecord:
    """Pure resolved fixed-autoencoder architecture contract."""

    identifier: str
    kind: str
    hidden_dims: tuple[PositiveInt, ...]
    bottleneck_dim: str
    activation: str
    activation_placement: str
    output_activation: str
    normalization_layers: str
    bias: bool
    reconstruction_objective: str
    training_loss_reduction: str
    precision: str
    input_dimension_resolution: str
    input_dimension_declared_per_dataset: bool
    input_dimension_validation: str
    decoder_construction: str
    decoder_final_layer_output_dim: str
    weight_initialization: str
    bias_initialization: str
    initialization_applied_to: str
    initialization_seeded_by: str
    anomaly_score_definition: str
    anomaly_score_orientation: str
