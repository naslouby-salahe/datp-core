"""Pure resolved records for model architecture, optimization, batching, training profiles, and checkpoints."""

from __future__ import annotations

from enum import StrEnum

from attrs import define

from datp_core.pipeline.identifiers import CheckpointProfileId, SeedCohortId, TrainingProfileId
from datp_core.pipeline.values import NonNegativeFloat, PositiveFloat, PositiveInt, Seed


class TrainingProfileKind(StrEnum):
    CENTRALIZED_POOLED_TRAINING = "centralized_pooled_training"
    DENSE_AUTOENCODER = "dense_autoencoder"
    FEDERATED_AVERAGING_TRAINING = "federated_averaging_training"
    FEDERATED_PROX_TRAINING = "federated_prox_training"


class PersonalizationStrategy(StrEnum):
    NONE = "none"
    DITTO = "ditto"


class CheckpointAuthorization(StrEnum):
    PRIMARY_SELECTION_COMPUTED_ONCE = "primary_selection_computed_once_on_natural_device_regime"
    LOOKUP_OF_FEDERATED_AVERAGING = "lookup_of_federated_averaging_primary_selection"
    HISTORICAL_FIRST_QUALIFYING_ROUND = "historical_first_qualifying_round_or_150_round_cap"
    INDEPENDENT_SELECTION = (
        "independent_selection_own_non_federated_curve_never_fused_with_federated_averaging_artifacts"
    )


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


@define(frozen=True, slots=True, kw_only=True)
class OptimizerRecord:
    """Pure resolved optimizer contract."""

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


@define(frozen=True, slots=True, kw_only=True)
class BatchingRecord:
    """Pure resolved batching contract."""

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


@define(frozen=True, slots=True, kw_only=True)
class FederationProfileRecord:
    """Pure resolved Flower participation contract."""

    fraction_fit: float
    fraction_evaluate: float
    minimum_fit_clients: PositiveInt
    minimum_evaluate_clients: PositiveInt
    minimum_available_clients: PositiveInt


@define(frozen=True, slots=True, kw_only=True)
class TrainingProfileRecord:
    identifier: TrainingProfileId
    kind: TrainingProfileKind
    model_architecture_id: str
    optimizer_id: str
    batching_profile_id: str
    local_epochs: PositiveInt | None
    participation: str | None
    checkpoint_authorization: CheckpointAuthorization
    personalization: PersonalizationStrategy | None
    personalized_local_epochs: PositiveInt | None
    personalization_parameter_grid: tuple[float, ...] | None
    proximal_objective: str | None
    mu_grid: tuple[float, ...] | None
    mu_zero_forbidden_as_a_fedprox_condition: bool | None
    federation: FederationProfileRecord | None


@define(frozen=True, slots=True, kw_only=True)
class CheckpointConvergenceRecord:
    """Pure resolved historical convergence rule (anchor terminal-checkpoint selection)."""

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


@define(frozen=True, slots=True, kw_only=True)
class CheckpointSelectionRecord:
    """Pure resolved checkpoint selection contract."""

    rule: str
    tie_break: str | None
    scope: str | None
    aggregation: str | None
    selected_round_reuse: str | None
    selection_granularity: str | None
    forbidden_selectors: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class CheckpointProfileRecord:
    identifier: CheckpointProfileId
    total_rounds: PositiveInt | None
    selected_rounds: tuple[PositiveInt, ...]
    early_stopping: str
    selection_rule: str
    selection: CheckpointSelectionRecord
    convergence: CheckpointConvergenceRecord | None
    checkpoint_save_policy: str | None


@define(frozen=True, slots=True, kw_only=True)
class SeedCohortRecord:
    identifier: SeedCohortId
    paired_seed_count: PositiveInt
    training_seeds: tuple[Seed, ...]
    bootstrap_analysis_seed: Seed
    analysis_seed_model: str
