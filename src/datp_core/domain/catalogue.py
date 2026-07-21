"""Pure resolved experiment catalogue records."""

from __future__ import annotations

from enum import Enum

from attrs import define, field

from datp_core.domain.fingerprints import Fingerprint
from datp_core.domain.identifiers import (
    CheckpointProfileId,
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    ExperimentId,
    MetricBundleId,
    NormalizationStrategyId,
    PopulationId,
    SeedCohortId,
    StatisticalProfileId,
    ThresholdPolicyId,
    TrainingProfileId,
)
from datp_core.domain.values import (
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    Probability,
    Seed,
    TypedDomainRegistry,
)


class EvidenceRole(Enum):
    ANCHOR = "anchor"
    CONFIRMATORY = "confirmatory"
    SENSITIVITY = "sensitivity"
    EXPLORATORY = "exploratory"
    STRESS_TEST = "stress_test"
    COMPARATOR = "comparator"
    MECHANISM = "mechanism"
    SUPPORTIVE = "supportive"
    BOUNDARY = "boundary"
    EXTERNAL_VALIDATION = "external_validation"


class RunRequirement(Enum):
    MANDATORY = "mandatory"
    CONDITIONAL = "conditional"
    EXPLORATORY = "exploratory"
    OPTIONAL = "optional"


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
class EligibilityFallbackRecord:
    """Pure resolved deployment fallback for ineligible clients."""

    threshold_source: str
    shared_construction: str
    reported_status: str
    enters_primary_dispersion: bool


@define(frozen=True, slots=True, kw_only=True)
class EligibilityPolicyRecord:
    """Pure resolved client eligibility policy."""

    identifier: EligibilityPolicyId
    minimum_benign_calibration_count: PositiveInt
    determined_before_test_evaluation: bool
    identical_across_policies_in_one_comparison: bool
    fpr_evaluable_requires_non_empty_benign_test_denominator: bool
    attack_evaluable_requires: tuple[str, ...]
    ineligible_clients_excluded_from_primary_dispersion: bool
    ineligible_client_deployment_fallback: EligibilityFallbackRecord
    zero_eligible_clients_behavior: str
    affects_standard_eligibility_minimum: bool | None
    permitted_use: str | None


@define(frozen=True, slots=True, kw_only=True)
class NormalizationStrategyRecord:
    """Pure resolved normalization strategy."""

    identifier: NormalizationStrategyId
    formula: str
    fitted_statistics: tuple[str, ...]
    constant_feature_rule: str
    out_of_range_transform_values: str
    fit_population: str
    standard_deviation_ddof: int | None


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimatorRecord:
    """Pure resolved quantile estimator contract."""

    identifier: str
    sort_order: str
    index_formula: str
    interpolation: str
    single_element_behavior: str
    empty_input_behavior: str
    non_finite_input_behavior: str
    tie_behavior: str


@define(frozen=True, slots=True, kw_only=True)
class MetricBundleRecord:
    """Pure resolved metric bundle."""

    identifier: MetricBundleId
    metrics: tuple[str, ...]
    cross_client_aggregation: str | None
    primary_dispersion_metric: str | None
    model_quality_control: str | None
    excludes_ineligible_clients: bool | None
    requires_attack_evaluable_clients: bool | None


@define(frozen=True, slots=True, kw_only=True)
class TrainingProfileRecord:
    identifier: TrainingProfileId
    kind: str
    model_architecture_id: str
    optimizer_id: str
    batching_profile_id: str
    local_epochs: PositiveInt | None
    participation: str | None
    checkpoint_authorization: str
    personalization: str | None
    federation: FederationProfileRecord | None


@define(frozen=True, slots=True, kw_only=True)
class FederationProfileRecord:
    """Pure resolved Flower participation contract."""

    fraction_fit: float
    fraction_evaluate: float
    minimum_fit_clients: PositiveInt
    minimum_evaluate_clients: PositiveInt
    minimum_available_clients: PositiveInt


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


@define(frozen=True, slots=True, kw_only=True)
class StatisticalProfileRecord:
    """Resolved, executable statistical analysis contract."""

    identifier: StatisticalProfileId
    method: str | None
    confidence_level: Probability | None
    resample_count: PositiveInt | None
    minimum_units: PositiveInt | None


@define(frozen=True, slots=True, kw_only=True)
class CapabilityRequirementRecord:
    capability: str
    when_unavailable: str


@define(frozen=True, slots=True, kw_only=True)
class EvaluationSpecRecord:
    label: str
    threshold_policy_id: ThresholdPolicyId
    run_requirement: RunRequirement


@define(frozen=True, slots=True, kw_only=True)
class AnalysisSpecRecord:
    label: str
    kind: str
    result_type: str
    primary_metric: str | None
    statistical_profile: str | None


SweepValue = str | int | float | tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ValueSweepRecord:
    """A sweep over an explicit authored list of scalar or list-of-string values."""

    name: str
    values: tuple[SweepValue, ...]


@define(frozen=True, slots=True, kw_only=True)
class SweepConditionRecord:
    name: str
    allocation: str
    dirichlet_alpha: float | None


@define(frozen=True, slots=True, kw_only=True)
class ConditionSweepRecord:
    """A sweep over named authored partition/allocation conditions."""

    name: str
    conditions: tuple[SweepConditionRecord, ...]


SweepRecord = ValueSweepRecord | ConditionSweepRecord


@define(frozen=True, slots=True, kw_only=True)
class PopulationRecord:
    identifier: PopulationId
    dataset_id: DatasetId
    setup_id: DatasetSetupId
    metric_bundle_id: MetricBundleId


@define(frozen=True, slots=True, kw_only=True)
class ExperimentRecord:
    identifier: ExperimentId
    display_name: str
    evidence_role: EvidenceRole
    run_requirement: RunRequirement
    population_ids: tuple[PopulationId, ...]
    training_profile_id: TrainingProfileId
    checkpoint_profile_id: CheckpointProfileId
    seed_cohort_id: SeedCohortId
    eligibility_policy_id: EligibilityPolicyId
    prerequisite_ids: tuple[ExperimentId, ...]
    capability_requirements: tuple[CapabilityRequirementRecord, ...]
    evaluations: tuple[EvaluationSpecRecord, ...]
    analyses: tuple[AnalysisSpecRecord, ...]
    report_ids: tuple[str, ...]
    sweeps: tuple[SweepRecord, ...] = field(factory=tuple)


@define(frozen=True, slots=True, kw_only=True)
class ResolvedCatalogue:
    schema_version: PositiveInt
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfileRecord]
    checkpoint_profiles: TypedDomainRegistry[CheckpointProfileId, CheckpointProfileRecord]
    seed_cohorts: TypedDomainRegistry[SeedCohortId, SeedCohortRecord]
    fingerprint: Fingerprint
