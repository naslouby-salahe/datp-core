"""Cross-cutting analysis contracts shared by multiple capability modules."""

from __future__ import annotations

from typing import ClassVar, Protocol, runtime_checkable

from attrs import define

from datp_core.analysis.enums import (
    AlertBurdenStatus,
    AlternativeHypothesis,
    AnalysisResultKind,
    AnchorCheckIdentifier,
    AnchorComparisonMode,
    ChronologyPolicy,
    ClusterDispersionStatus,
    CommunicationFieldIdentifier,
    ConfidenceIntervalMethod,
    CoverageDirection,
    CoverageStatus,
    HypothesisTestName,
    NegativeRecoveryBehavior,
    ProducedField,
    ReplicateAggregation,
    ResourceEstimateBasis,
    SweepDimensionKind,
    TemporalOutcomeBand,
    UndefinedDenominatorBehavior,
)
from datp_core.analysis.errors import PrerequisiteResultMissingError, StatisticalProcedureError
from datp_core.analysis.runtime.registry import RESULT_REGISTRY
from datp_core.core.identifiers import (
    AnalysisLabel,
    ClientId,
    ClusterLabel,
    EvaluationLabel,
    ExperimentId,
    MetricId,
    PartitionConditionId,
    ThresholdPolicyId,
)
from datp_core.core.numbers import Probability
from datp_core.core.seeding import Seed
from datp_core.evaluation.distributions import ClientScoreDistributionRecord, ThresholdTradeoffEntry
from datp_core.thresholding.policies.enums import ConformalAttainabilityStatus


@runtime_checkable
class QuantileThresholdPolicy(Protocol):
    """A threshold policy that exposes a quantile value."""

    quantile: float


@runtime_checkable
class AnalysisResultContract(Protocol):
    """Protocol for every persisted analysis result."""

    result_kind: ClassVar[AnalysisResultKind]
    payload_version: ClassVar[int]


@define(frozen=True, slots=True, kw_only=True)
class AnalysisCell:
    """Explicit immutable record representing one cell in a sweep dimension."""

    dimension: SweepDimensionKind
    value: float | int | str | tuple[str, ...] | PartitionConditionId


@define(frozen=True, slots=True, kw_only=True)
class PairedAnalysisCell:
    """One valid combination of sweep dimensions for a paired-threshold analysis."""

    partition_condition: PartitionConditionId | None = None
    proximal_mu: float | None = None
    ditto_weight: float | None = None
    threshold_quantile: float | None = None
    shrinkage_weight: float | None = None
    calibration_sample_count: int | None = None



@define(frozen=True, slots=True, kw_only=True)
class ConfidenceInterval:
    """A confidence interval with its construction method."""

    lower_bound: float
    upper_bound: float
    confidence_level: Probability
    method: ConfidenceIntervalMethod

    def __attrs_post_init__(self) -> None:
        if self.lower_bound > self.upper_bound:
            raise StatisticalProcedureError(
                f"Confidence interval lower bound {self.lower_bound} exceeds upper bound {self.upper_bound}"
            )

    @property
    def excludes_zero_positive(self) -> bool:
        return self.lower_bound > 0.0


@define(frozen=True, slots=True, kw_only=True)
class HypothesisTestResult:
    """Result of a statistical hypothesis test."""

    test_name: HypothesisTestName
    statistic: float
    p_value: float
    degrees_of_freedom: float | None = None
    alternative: AlternativeHypothesis = AlternativeHypothesis.TWO_SIDED


@define(frozen=True, slots=True, kw_only=True)
class LinearRegressionResult:
    """Simple linear regression with leverage diagnostics."""

    slope: float
    intercept: float
    standard_error: float
    r_squared: float
    leverage: tuple[float, ...]
    leave_one_out_slopes: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class PairedSeedDifferenceRecord:
    """One paired-seed statistical comparison between two threshold policies."""

    metric_id: MetricId
    policy_a_id: ThresholdPolicyId
    policy_b_id: ThresholdPolicyId
    mean_difference: float
    confidence_interval: ConfidenceInterval
    resample_count: int
    analysis_seed: Seed
    hypothesis_test: HypothesisTestResult | None = None
    effect_size: float | None = None


# ---------------------------------------------------------------------------
# Result Classes Implementing AnalysisResultContract
# ---------------------------------------------------------------------------


@define(frozen=True, slots=True, kw_only=True)
class PairedThresholdAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.PAIRED_THRESHOLD
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    metric: MetricId
    first_threshold_policy: ThresholdPolicyId
    second_threshold_policy: ThresholdPolicyId
    training_seeds: tuple[Seed, ...]
    first_seed_values: tuple[float, ...]
    second_seed_values: tuple[float, ...]
    first_mean: float
    second_mean: float
    mean_difference: float
    confidence_interval: ConfidenceInterval
    p_value: float | None
    rank_biserial: float | None
    resample_count: int
    analysis_seed: Seed
    seed_differences: tuple[float, ...]
    sign_consistency: float
    zero_difference_count: int
    negative_difference_count: int
    partition_condition: PartitionConditionId | None = None
    federated_proximal_mu: float | None = None
    ditto_proximal_weight: float | None = None
    threshold_quantile: float | None = None
    shrinkage_weight: float | None = None
    calibration_sample_count: int | None = None
    holm_adjusted_p_value: float | None = None


@define(frozen=True, slots=True, kw_only=True)
class FederatedProximalLossObservation:
    proximal_mu: float
    mean_benign_calibration_loss: float


@define(frozen=True, slots=True, kw_only=True)
class DittoLossObservation:
    proximal_weight: float
    mean_benign_calibration_loss: float


@define(frozen=True, slots=True, kw_only=True)
class CheckpointSelectionArtifact:
    selected_proximal_mu: float | None = None
    selected_ditto_proximal_weight: float | None = None
    locked_primary_round: int | None = None
    federated_proximal_losses: tuple[FederatedProximalLossObservation, ...] = ()
    ditto_losses: tuple[DittoLossObservation, ...] = ()


@define(frozen=True, slots=True, kw_only=True)
class FederatedProximalSelectionResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.FEDERATED_PROXIMAL_SELECTION
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    selected_proximal_mu: float
    locked_primary_round: int | None
    calibration_losses: tuple[FederatedProximalLossObservation, ...] | None


@define(frozen=True, slots=True, kw_only=True)
class DittoSelectionResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.DITTO_SELECTION
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    selected_ditto_proximal_weight: float
    locked_primary_round: int | None
    calibration_losses: tuple[DittoLossObservation, ...] | None


@define(frozen=True, slots=True, kw_only=True)
class AnchorHistoricalReference:
    delta: float
    lower_bound: float
    upper_bound: float
    interval_width: float


@define(frozen=True, slots=True, kw_only=True)
class AnchorEquivalenceChecks:
    positive_reproduced_delta: bool
    reproduced_estimate_within_historical_interval: bool
    overlapping_confidence_intervals: bool
    no_material_movement_toward_zero: bool
    reproduced_interval_width_at_most_1_20x_historical_width: bool
    verified_configuration_and_provenance: bool


@define(frozen=True, slots=True, kw_only=True)
class AnchorEquivalenceAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.ANCHOR_EQUIVALENCE
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    comparison_mode: AnchorComparisonMode
    source_analysis: AnalysisLabel
    passed: bool
    failure_reasons: tuple[AnchorCheckIdentifier, ...]
    checks: AnchorEquivalenceChecks
    reproduced_delta: float
    reproduced_confidence_interval: tuple[float, float]
    historical_reference: AnchorHistoricalReference


@define(frozen=True, slots=True, kw_only=True)
class ConformalClientCoverageRecord:
    client_id: ClientId
    coverage: float | None
    absolute_coverage_error: float | None
    coverage_status: CoverageStatus
    finite_sample_rank: int
    attainability_status: ConformalAttainabilityStatus
    calibration_count: int


@define(frozen=True, slots=True, kw_only=True)
class ConformalSeedCoverageResult:
    seed: Seed
    per_client_coverage: tuple[ConformalClientCoverageRecord, ...]
    benign_true_negatives: int
    benign_total: int


@define(frozen=True, slots=True, kw_only=True)
class ConformalCoverageAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.CONFORMAL_COVERAGE
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    target_coverage: float
    achieved_marginal_coverage: float | None
    achieved_macro_client_coverage: float | None
    absolute_coverage_error: float | None
    coverage_direction: CoverageDirection | None
    seed_results: tuple[ConformalSeedCoverageResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimationClientResult:
    client_id: ClientId
    absolute_threshold_error: float
    relative_threshold_error: float | None
    achieved_exceedance: float | None
    signed_attainment_error: float | None
    absolute_attainment_error: float | None


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimationEvaluationResult:
    evaluation_label: EvaluationLabel
    per_client: tuple[QuantileEstimationClientResult, ...]
    within_term: float
    between_term: float
    between_ratio: float | None


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimationSeedResult:
    seed: Seed
    oracle_threshold: float
    evaluations: tuple[QuantileEstimationEvaluationResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimationAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.QUANTILE_ESTIMATION
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    produced_fields: tuple[ProducedField, ...]
    seed_results: tuple[QuantileEstimationSeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class ThresholdStabilitySeedResult:
    seed: Seed
    threshold_variance_across_replicates: float | None
    absolute_attainment_error: float | None
    worst_client_fpr: float | None
    clients_unavailable_at_size: tuple[ClientId, ...]


@define(frozen=True, slots=True, kw_only=True)
class ThresholdStabilityAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.THRESHOLD_STABILITY
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    calibration_sample_count: int
    replicate_aggregation: ReplicateAggregation
    independent_inferential_unit: str
    seed_results: tuple[ThresholdStabilitySeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class AssociationCorrelationResult:
    coefficient: float
    p_value: float


@define(frozen=True, slots=True, kw_only=True)
class AssociationRegressionResult:
    coefficient: float
    intercept: float
    standard_error: float
    r_squared: float
    leverage: tuple[float, ...]
    leave_one_out_slopes: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class AssociationObservationRecord:
    partition_condition: PartitionConditionId
    seed: Seed
    pairwise_js_divergence: float
    cv_fpr_delta: float


@define(frozen=True, slots=True, kw_only=True)
class MetricAssociationAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.METRIC_ASSOCIATION
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    interpretation_constraint: str
    spearman: AssociationCorrelationResult
    linear_regression: AssociationRegressionResult
    observations: tuple[AssociationObservationRecord, ...]


@define(frozen=True, slots=True, kw_only=True)
class CountRatioObservation:
    """Observation pair of numerator and denominator counts/totals for ratio-of-totals calculation."""

    numerator: float
    denominator: float


@define(frozen=True, slots=True, kw_only=True)
class PrerequisiteAnalysisReference:
    """Typed reference coordinates for resolving a prerequisite analysis result."""

    experiment_id: ExperimentId
    analysis_label: AnalysisLabel
    result_kind: AnalysisResultKind


@define(frozen=True, slots=True, kw_only=True)
class AbsorptionAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.ABSORPTION
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    formula: str
    undefined_denominator_behavior: UndefinedDenominatorBehavior
    per_seed_ratio: tuple[float | None, ...]
    defined_seed_count: int
    mean_defined_ratio: float | None
    ratio_of_seed_means: float | None


@define(frozen=True, slots=True, kw_only=True)
class RecoveryFractionAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.RECOVERY_FRACTION
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    formula: str
    undefined_denominator_behavior: UndefinedDenominatorBehavior
    per_seed_recovery_fraction: tuple[float | None, ...]
    defined_seed_count: int
    mean_defined_recovery_fraction: float | None


@define(frozen=True, slots=True, kw_only=True)
class ClientClusterMembership:
    client_id: ClientId
    cluster_label: ClusterLabel


@define(frozen=True, slots=True, kw_only=True)
class ClusterSize:
    cluster_label: ClusterLabel
    client_count: int


@define(frozen=True, slots=True, kw_only=True)
class ClusterDispersionResult:
    status: ClusterDispersionStatus
    value: float | None
    reason: str | None
    observed_cluster_count: int
    available_cluster_count: int
    excluded_client_count: int


@define(frozen=True, slots=True, kw_only=True)
class ClusterAblationObservation:
    seed: Seed
    fingerprint_features: tuple[str, ...]
    adjusted_rand_index: float


@define(frozen=True, slots=True, kw_only=True)
class ClusterAblationStabilityResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.CLUSTER_ABLATION
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    comparison_unit: str
    reference_evaluation: EvaluationLabel
    observations: tuple[ClusterAblationObservation, ...]


@define(frozen=True, slots=True, kw_only=True)
class ClusterStabilitySeedSummary:
    seed: Seed
    cluster_memberships: tuple[ClientClusterMembership, ...]
    cluster_sizes: tuple[ClusterSize, ...]
    singleton_cluster_flag: bool
    empty_cluster_flag: bool
    within_cluster_threshold_dispersion: ClusterDispersionResult
    within_cluster_fpr_dispersion: ClusterDispersionResult
    across_cluster_threshold_dispersion: ClusterDispersionResult
    across_cluster_mean_fpr_dispersion: ClusterDispersionResult


@define(frozen=True, slots=True, kw_only=True)
class ClusterMembershipStabilityResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.CLUSTER_STABILITY
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    comparison_unit: str
    seed_summaries: tuple[ClusterStabilitySeedSummary, ...]
    adjusted_rand_index: tuple[float, ...]
    mean_adjusted_rand_index: float | None


ClusterStabilityAnalysisResult = ClusterAblationStabilityResult | ClusterMembershipStabilityResult


@define(frozen=True, slots=True, kw_only=True)
class ClientDistributionEntry:
    client_id: ClientId
    distribution: ClientScoreDistributionRecord


@define(frozen=True, slots=True, kw_only=True)
class EvaluationDistributionResult:
    evaluation_label: EvaluationLabel
    clients: tuple[ClientDistributionEntry, ...]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismSeedResult:
    seed: Seed
    evaluations: tuple[EvaluationDistributionResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismRawResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.DISTRIBUTION_MECHANISM
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    produced_fields: tuple[ProducedField, ...]
    seed_results: tuple[DistributionMechanismSeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class ClientTradeoffEntry:
    client_id: ClientId
    tradeoff: ThresholdTradeoffEntry


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismTradeoffSeedResult:
    seed: Seed
    per_client_tradeoff: tuple[ClientTradeoffEntry, ...]


@define(frozen=True, slots=True, kw_only=True)
class FieldFormulaContract:
    field: ProducedField
    formula: str


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismTradeoffResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.DISTRIBUTION_TRADEOFF
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    field_formulas: tuple[FieldFormulaContract, ...]
    produced_fields: tuple[ProducedField, ...]
    seed_results: tuple[DistributionMechanismTradeoffSeedResult, ...]


DistributionMechanismAnalysisResult = DistributionMechanismRawResult | DistributionMechanismTradeoffResult


@define(frozen=True, slots=True, kw_only=True)
class LockedClientDistributionAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.LOCKED_CLIENT_DISTRIBUTION
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    locked_client_identifier: ClientId
    produced_fields: tuple[ProducedField, ...]
    seed_results: tuple[DistributionMechanismSeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class TemporalRecoveryAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.TEMPORAL_RECOVERY
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    metric: MetricId
    static_reference_cv: tuple[float, ...]
    frozen_future_cv: tuple[float, ...]
    recalibrated_future_cv: tuple[float, ...]
    drift_excess: tuple[float, ...]
    recovered_amount: tuple[float, ...]
    recovery_ratio: tuple[float | None, ...]
    meaningful_degradation: bool
    drift_confidence_interval: tuple[float, float]
    outcome_band: TemporalOutcomeBand
    defined_recovery_ratio_seed_count: int
    mean_defined_recovery_ratio: float | None
    negative_recovery_policy: NegativeRecoveryBehavior
    chronology_unverifiable_policy: ChronologyPolicy


@define(frozen=True, slots=True, kw_only=True)
class AlertBurdenAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.ALERT_BURDEN
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    formula: str
    status: AlertBurdenStatus
    reason: str
    alerts_per_client_per_day: float | None = None
    benign_decision_rate_source: str | None = None


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostEvaluationResult:
    evaluation: EvaluationLabel
    transmitted_field_list: tuple[CommunicationFieldIdentifier, ...]
    estimated_threshold_message_bytes: int
    estimated_model_exchange_bytes_per_round: int
    estimated_checkpoint_storage_bytes: int


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostSeedResult:
    seed: Seed
    evaluations: tuple[ResourceCostEvaluationResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostAnalysisResult:
    result_kind: ClassVar[AnalysisResultKind] = AnalysisResultKind.RESOURCE_COST
    payload_version: ClassVar[int] = 1

    analysis_label: AnalysisLabel
    estimate_basis: ResourceEstimateBasis
    produced_fields: tuple[ProducedField, ...]
    seed_results: tuple[ResourceCostSeedResult, ...]


# ---------------------------------------------------------------------------
# Prerequisite Results
# ---------------------------------------------------------------------------


@define(frozen=True, slots=True, kw_only=True)
class PrerequisiteExperimentResult:
    """A validated, immutable frozen result supplied by a configured prerequisite."""

    experiment_id: ExperimentId
    frozen_result_path: str
    frozen_result_checksum: str
    scientific_fingerprint: str
    statistical_results: tuple[AnalysisResultContract, ...]

    def paired_result(self, analysis_label: AnalysisLabel) -> PairedThresholdAnalysisResult:
        """Return the unique paired result matching *analysis_label*."""
        matches = tuple(
            item
            for item in self.statistical_results
            if isinstance(item, PairedThresholdAnalysisResult) and item.analysis_label == analysis_label
        )
        if len(matches) != 1:
            raise PrerequisiteResultMissingError(
                f"Prerequisite '{self.experiment_id.value}' has no unique paired result "
                f"for analysis '{analysis_label.value}'"
            )
        return matches[0]


for _cls in (
    PairedThresholdAnalysisResult,
    ConformalCoverageAnalysisResult,
    QuantileEstimationAnalysisResult,
    ThresholdStabilityAnalysisResult,
    MetricAssociationAnalysisResult,
    AbsorptionAnalysisResult,
    RecoveryFractionAnalysisResult,
    ClusterAblationStabilityResult,
    ClusterMembershipStabilityResult,
    DistributionMechanismRawResult,
    DistributionMechanismTradeoffResult,
    LockedClientDistributionAnalysisResult,
    TemporalRecoveryAnalysisResult,
    AlertBurdenAnalysisResult,
    ResourceCostAnalysisResult,
    FederatedProximalSelectionResult,
    DittoSelectionResult,
    AnchorEquivalenceAnalysisResult,
):
    RESULT_REGISTRY.register_result_class(_cls)

