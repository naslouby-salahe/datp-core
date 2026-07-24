"""Authored model architecture, optimizer, batching, determinism, seed cohort, checkpoint, and
training profile contracts (protocols.yaml)."""

from __future__ import annotations

from typing import Literal

from pydantic import JsonValue, model_validator

from datp_core.config.authored.base import StrictFrozenConfigModel


class ModelInputDimensionConfig(StrictFrozenConfigModel):
    resolution: str
    declared_per_dataset: bool
    validation: str


class ModelDecoderConfig(StrictFrozenConfigModel):
    construction: str
    final_layer_output_dim: str


class ModelParameterInitializationConfig(StrictFrozenConfigModel):
    weight: str
    bias: str
    applied_to: str
    seeded_by: str


class ModelAnomalyScoreConfig(StrictFrozenConfigModel):
    definition: str
    orientation: str


class ModelArchitectureConfig(StrictFrozenConfigModel):
    kind: Literal["dense_autoencoder"]
    input_dimension: ModelInputDimensionConfig
    hidden_dims: list[int]
    bottleneck_dim: str
    decoder: ModelDecoderConfig
    activation: str
    activation_placement: str
    output_activation: str
    normalization_layers: str
    bias: bool
    parameter_initialization: ModelParameterInitializationConfig
    reconstruction_objective: str
    training_loss_reduction: str
    anomaly_score: ModelAnomalyScoreConfig
    precision: str


class OptimizerProfileConfig(StrictFrozenConfigModel):
    optimizer_type: str
    learning_rate: float
    beta_1: float
    beta_2: float
    epsilon: float
    weight_decay: float
    amsgrad: bool
    scheduler: str
    gradient_clipping: str
    state_lifecycle: str
    state_aggregated_by_server: bool


class BatchingProfileConfig(StrictFrozenConfigModel):
    micro_batch_size: int
    gradient_accumulation_steps: int
    effective_batch_size: int
    shuffle_each_epoch: bool
    shuffle_unit: str
    incomplete_final_batch: str
    row_ordering_before_shuffle: str
    shuffle_seed_namespace: str
    worker_seed_namespace: str


class SeedNamespaceConfig(StrictFrozenConfigModel):
    key: str
    components: list[str]


class DeterminismProfileConfig(StrictFrozenConfigModel):
    seed_domains: list[str]
    partition_seed_independent_of_training_seeds: bool
    checkpoint_selection_uses_no_stochastic_seed: bool
    derived_seed_algorithm: dict[str, str | int]
    seed_namespaces: dict[str, SeedNamespaceConfig]
    resolved_seeds_required_in_manifests: list[str]


class SeedCohortConfig(StrictFrozenConfigModel):
    paired_seed_count: int
    training_seeds: list[int]
    bootstrap_analysis_seed: int
    analysis_seed_model: str

    @model_validator(mode="after")
    def validate_seed_cohort(self) -> SeedCohortConfig:
        if len(self.training_seeds) != self.paired_seed_count:
            raise ValueError("paired_seed_count must equal the number of training_seeds")
        if len(set(self.training_seeds)) != len(self.training_seeds):
            raise ValueError("training_seeds must be unique")
        return self


class CheckpointSelectorInputConfig(StrictFrozenConfigModel):
    population: str
    quantity: str
    client_weighting: str | None = None
    aggregation_over_clients: str | None = None
    client_accumulation_order: str | None = None
    aggregation_over_rows: str | None = None


class CheckpointSelectionConfig(StrictFrozenConfigModel):
    rule: str
    selector_input: CheckpointSelectorInputConfig | None = None
    tie_break: str | None = None
    aggregation: str | None = None
    scope: str | None = None
    selected_round_reuse: str | None = None
    weights_remain_seed_and_population_specific: bool | None = None
    forbidden_selectors: list[str] | None = None
    selection_granularity: str | None = None


class CheckpointConvergenceConfig(StrictFrozenConfigModel):
    metric: str
    rounds_initial: int
    rule: str
    formula: str
    zero_start_loss_behavior: str
    tolerance: float
    window_rounds: int
    window: str
    qualification: str
    no_qualifying_round_behavior: str


class CheckpointProfileConfig(StrictFrozenConfigModel):
    total_rounds: int | None = None
    total_epochs: int | None = None
    rounds: list[int] | None = None
    epochs: list[int] | None = None
    early_stopping: str
    convergence: CheckpointConvergenceConfig | None = None
    convergence_logged_without_stopping: bool | None = None
    checkpoint_save_policy: str | None = None
    selection: CheckpointSelectionConfig


class FederationStrategyConfig(StrictFrozenConfigModel):
    """Authored Flower FedAvg participation contract."""

    fraction_fit: float
    fraction_evaluate: float
    minimum_fit_clients: int
    minimum_evaluate_clients: int
    minimum_available_clients: int


class TrainingProfileConfig(StrictFrozenConfigModel):
    kind: str
    model_architecture: str
    optimizer: str
    batching: str
    local_epochs: int | None = None
    participation: str | None = None
    participation_rule: str | None = None
    client_ordering: str | None = None
    client_update_weighting: str | None = None
    aggregation_formula: str | None = None
    aggregation_accumulation_order: str | None = None
    personalization: str | None = None
    checkpoint_authorization: str
    personalized_local_epochs: int | None = None
    personalization_proximal_weight: float | None = None
    personalization_parameter_grid: list[float] | None = None
    personalization_parameter_selection: dict[str, JsonValue] | None = None
    ditto_specification: dict[str, JsonValue] | None = None
    proximal_objective: str | None = None
    mu: float | None = None
    mu_grid: list[float] | None = None
    mu_resolution: str | None = None
    mu_zero_forbidden_as_a_fedprox_condition: bool | None = None
    training_population: str | None = None
    row_ordering_before_shuffle: str | None = None
    validation_split: dict[str, JsonValue] | None = None
    federation: FederationStrategyConfig | None = None


class NormalizationStrategyConfig(StrictFrozenConfigModel):
    formula: str
    fitted_statistics: list[str]
    constant_feature_rule: str
    out_of_range_transform_values: str
    fit_population: str
    standard_deviation_ddof: int | None = None
