"""Typed per-analysis-family RESULT hierarchy (paired threshold, association, stability, recovery
fraction, absorption, anchor equivalence, temporal recovery, cluster stability, conformal
coverage, distribution mechanism, locked-client distribution, alert burden, quantile estimation,
resource cost). These are immutable result structures only -- the analysis algorithms that build
them live in ``analysis/{paired,association,stability,coverage,ratios,operational,distributions}.py``
and ``analysis/execution.py``.
"""

from __future__ import annotations

from collections.abc import Mapping

from attrs import asdict, define

from datp_core.analysis.statistics import ConfidenceInterval
from datp_core.evaluation.distributions import ClientScoreDistributionRecord, ThresholdTradeoffEntry


@define(frozen=True, slots=True, kw_only=True)
class PairedThresholdAnalysisResult:
    analysis_label: str
    metric: str
    first_threshold_policy: str
    second_threshold_policy: str
    training_seeds: tuple[int, ...]
    first_seed_values: tuple[float, ...]
    second_seed_values: tuple[float, ...]
    first_mean: float
    second_mean: float
    mean_difference: float
    confidence_interval: ConfidenceInterval
    p_value: float | None
    rank_biserial: float | None
    resample_count: int
    analysis_seed: int
    seed_differences: tuple[float, ...]
    sign_consistency: float
    zero_difference_count: int
    negative_difference_count: int
    partition_condition: str | None = None
    federated_proximal_mu: float | None = None
    ditto_proximal_weight: float | None = None
    threshold_quantile: float | None = None
    shrinkage_weight: float | None = None
    calibration_sample_count: int | None = None
    holm_adjusted_p_value: float | None = None


@define(frozen=True, slots=True, kw_only=True)
class FederatedProximalSelectionResult:
    analysis_label: str
    selected_proximal_mu: float
    locked_primary_round: int | None
    mean_benign_calibration_loss_by_mu: Mapping[str, float] | None


@define(frozen=True, slots=True, kw_only=True)
class DittoSelectionResult:
    analysis_label: str
    selected_ditto_proximal_weight: float
    locked_primary_round: int | None
    mean_benign_calibration_loss_by_weight: Mapping[str, float] | None


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
    partition_condition: str
    seed: int
    pairwise_js_divergence: float
    cv_fpr_delta: float


@define(frozen=True, slots=True, kw_only=True)
class MetricAssociationAnalysisResult:
    analysis_label: str
    interpretation_constraint: str
    spearman: AssociationCorrelationResult
    linear_regression: AssociationRegressionResult
    observations: tuple[AssociationObservationRecord, ...]


@define(frozen=True, slots=True, kw_only=True)
class ThresholdStabilitySeedResult:
    seed: int
    threshold_variance_across_replicates: float | None
    absolute_attainment_error: float | None
    worst_client_fpr: float | None
    clients_unavailable_at_size: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ThresholdStabilityAnalysisResult:
    analysis_label: str
    calibration_sample_count: int
    replicate_aggregation: str
    independent_inferential_unit: str
    seed_results: tuple[ThresholdStabilitySeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class RecoveryFractionAnalysisResult:
    analysis_label: str
    formula: str
    undefined_denominator_behavior: str
    per_seed_recovery_fraction: tuple[float | None, ...]
    defined_seed_count: int
    mean_defined_recovery_fraction: float | None


@define(frozen=True, slots=True, kw_only=True)
class SeedRatioResult:
    """Generic seed-indexed ratio-of-differences result, shared by absorption-style analyses."""

    analysis_label: str
    formula: str
    undefined_denominator_behavior: str
    per_seed_ratio: tuple[float | None, ...]
    defined_seed_count: int
    mean_defined_ratio: float | None
    ratio_of_seed_means: float | None


AbsorptionAnalysisResult = SeedRatioResult


@define(frozen=True, slots=True, kw_only=True)
class ConformalClientCoverageRecord:
    coverage: float | None
    absolute_coverage_error: float | None
    coverage_status: str
    finite_sample_rank: int
    attainability_status: str
    calibration_count: int


@define(frozen=True, slots=True, kw_only=True)
class ConformalSeedCoverageResult:
    seed: int
    per_client_coverage: Mapping[str, ConformalClientCoverageRecord]
    client_coverages: tuple[float, ...]
    finite_sample_rank: Mapping[str, int]
    attainability_status: Mapping[str, str]
    benign_true_negatives: int
    benign_total: int


@define(frozen=True, slots=True, kw_only=True)
class ConformalCoverageAnalysisResult:
    analysis_label: str
    target_coverage: float
    achieved_marginal_coverage: float | None
    achieved_macro_client_coverage: float | None
    per_client_coverage: tuple[Mapping[str, ConformalClientCoverageRecord], ...]
    absolute_coverage_error: float | None
    finite_sample_rank: tuple[Mapping[str, int], ...]
    attainability_status: tuple[Mapping[str, str], ...]
    coverage_direction: str | None
    seed_results: tuple[ConformalSeedCoverageResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismSeedResult:
    seed: int
    evaluations: Mapping[str, Mapping[str, ClientScoreDistributionRecord]]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismRawResult:
    analysis_label: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[DistributionMechanismSeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismTradeoffSeedResult:
    seed: int
    per_client_tradeoff: Mapping[str, ThresholdTradeoffEntry]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismTradeoffResult:
    analysis_label: str
    field_formulas: Mapping[str, str]
    produced_fields: tuple[str, ...]
    seed_results: tuple[DistributionMechanismTradeoffSeedResult, ...]


DistributionMechanismAnalysisResult = DistributionMechanismRawResult | DistributionMechanismTradeoffResult


@define(frozen=True, slots=True, kw_only=True)
class LockedClientDistributionAnalysisResult:
    analysis_label: str
    locked_client_identifier: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[DistributionMechanismSeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class AlertBurdenAnalysisResult:
    analysis_label: str
    formula: str
    status: str
    reason: str
    alerts_per_client_per_day: float | None = None
    benign_decision_rate_source: str | None = None


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimationClientResult:
    client_id: str
    absolute_threshold_error: float
    relative_threshold_error: float | None
    achieved_exceedance: float | None
    signed_attainment_error: float | None
    absolute_attainment_error: float | None


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimationEvaluationResult:
    per_client: tuple[QuantileEstimationClientResult, ...]
    within_term: float
    between_term: float
    between_ratio: float | None


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimationSeedResult:
    seed: int
    oracle_threshold: float
    evaluations: Mapping[str, QuantileEstimationEvaluationResult]


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimationAnalysisResult:
    analysis_label: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[QuantileEstimationSeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostEvaluationResult:
    evaluation: str
    transmitted_field_list: tuple[str, ...]
    estimated_threshold_message_bytes: int
    estimated_model_exchange_bytes_per_round: int
    estimated_checkpoint_storage_bytes: int


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostSeedResult:
    seed: int
    evaluations: tuple[ResourceCostEvaluationResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostAnalysisResult:
    analysis_label: str
    estimate_basis: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[ResourceCostSeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class ClusterAblationObservation:
    seed: int
    fingerprint_features: tuple[str, ...]
    adjusted_rand_index: float


@define(frozen=True, slots=True, kw_only=True)
class ClusterAblationStabilityResult:
    analysis_label: str
    comparison_unit: str
    reference_evaluation: str
    observations: tuple[ClusterAblationObservation, ...]


@define(frozen=True, slots=True, kw_only=True)
class ClusterStabilitySeedSummary:
    seed: int
    cluster_membership_per_client: Mapping[str, int]
    cluster_size: Mapping[str, int]
    singleton_cluster_flag: bool
    empty_cluster_flag: bool
    within_cluster_threshold_dispersion: float | None
    within_cluster_fpr_dispersion: float | None
    across_cluster_threshold_dispersion: float | None
    across_cluster_mean_fpr_dispersion: float | None


@define(frozen=True, slots=True, kw_only=True)
class ClusterMembershipStabilityResult:
    analysis_label: str
    comparison_unit: str
    seed_summaries: tuple[ClusterStabilitySeedSummary, ...]
    adjusted_rand_index: tuple[float, ...]
    mean_adjusted_rand_index: float | None


ClusterStabilityAnalysisResult = ClusterAblationStabilityResult | ClusterMembershipStabilityResult


@define(frozen=True, slots=True, kw_only=True)
class TemporalRecoveryAnalysisResult:
    analysis_label: str
    metric: str
    static_reference_cv: tuple[float, ...]
    frozen_future_cv: tuple[float, ...]
    recalibrated_future_cv: tuple[float, ...]
    drift_excess: tuple[float, ...]
    recovered_amount: tuple[float, ...]
    recovery_ratio: tuple[float | None, ...]
    meaningful_degradation: bool
    drift_confidence_interval: tuple[float, float]
    outcome_band: str
    defined_recovery_ratio_seed_count: int
    mean_defined_recovery_ratio: float | None
    negative_recovery_policy: str
    chronology_unverifiable_policy: str


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
    analysis_label: str
    comparison_mode: str
    source_analysis: str
    passed: bool
    failure_reasons: tuple[str, ...]
    checks: AnchorEquivalenceChecks
    reproduced_delta: float
    reproduced_confidence_interval: tuple[float, float]
    historical_reference: Mapping[str, float | str]


AnalysisResult = (
    PairedThresholdAnalysisResult
    | FederatedProximalSelectionResult
    | DittoSelectionResult
    | MetricAssociationAnalysisResult
    | ThresholdStabilityAnalysisResult
    | RecoveryFractionAnalysisResult
    | AbsorptionAnalysisResult
    | ConformalCoverageAnalysisResult
    | DistributionMechanismAnalysisResult
    | LockedClientDistributionAnalysisResult
    | AlertBurdenAnalysisResult
    | QuantileEstimationAnalysisResult
    | ResourceCostAnalysisResult
    | ClusterStabilityAnalysisResult
    | TemporalRecoveryAnalysisResult
    | AnchorEquivalenceAnalysisResult
)


def analysis_result_to_payload(result: AnalysisResult) -> dict[str, object]:
    """Convert one typed analysis result into the exact JSON-serializable shape persisted on disk.

    Uses ``attrs.asdict`` for structural recursion (nested attrs records and Mapping/tuple values
    all unstructure to plain JSON-safe types); the one authored dotted metric-formula key on
    ``AnchorEquivalenceChecks`` is restored explicitly since it cannot be a Python identifier.
    """
    payload = asdict(result, recurse=True)
    checks = payload.get("checks")
    if isinstance(checks, dict) and "reproduced_interval_width_at_most_1_20x_historical_width" in checks:
        checks["reproduced_interval_width_at_most_1.20x_historical_width"] = checks.pop(
            "reproduced_interval_width_at_most_1_20x_historical_width"
        )
    return payload
