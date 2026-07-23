"""Resolved statistical-profile configuration, statistical procedure primitives, and the typed
per-analysis-family RESULT hierarchy (paired threshold, association, stability, recovery fraction,
absorption, anchor equivalence, temporal recovery, cluster stability, conformal coverage,
distribution mechanism, locked-client distribution, alert burden, quantile estimation, resource
cost -- per architecture-refactor section 12.2), replacing the untyped ``dict[str, object]`` result
plumbing found in the pre-refactor ``application/analysis_stages.py``.

Pure data and pure math live here (mirroring ``thresholding/models.py``); the analysis-family
functions that read artifacts and build these records live in ``analysis/{paired,association,
stability,coverage,temporal,resources,distributions}.py`` and ``analysis/execution.py``.
"""

from __future__ import annotations
import math

from collections.abc import Iterable, Mapping
from math import isfinite
from typing import cast

import numpy as np
from attrs import asdict, define
from scipy import stats

from datp_core.evaluation.distributions import ClientScoreDistributionRecord, ThresholdTradeoffEntry
from datp_core.pipeline.identifiers import ExperimentId, MetricId, StatisticalProfileId, ThresholdPolicyId
from datp_core.pipeline.values import PositiveInt, Probability, Seed, TypedDomainRegistry


@define(frozen=True, slots=True, kw_only=True)
class StatisticalProfileRecord:
    """Resolved, executable statistical analysis contract (BCa/percentile bootstrap, Wilcoxon, etc.)."""

    identifier: StatisticalProfileId
    method: str | None
    confidence_level: Probability | None
    resample_count: PositiveInt | None
    minimum_units: PositiveInt | None


@define(frozen=True, slots=True, kw_only=True)
class FieldEncodingRecord:
    bytes_per_field: int
    byte_order: str


@define(frozen=True, slots=True, kw_only=True)
class ThresholdExchangeEntryRecord:
    uplink_fields_per_client: tuple[str, ...] | None
    downlink_fields_per_client: tuple[str, ...] | None
    candidate_grid_downlink_fields_per_client: tuple[str, ...] | None
    candidate_grid_uplink_fields_per_client_per_candidate: tuple[str, ...] | None


@define(frozen=True, slots=True, kw_only=True)
class ThresholdExchangeRecord:
    direction: str
    b1: ThresholdExchangeEntryRecord
    b2: ThresholdExchangeEntryRecord
    b4: ThresholdExchangeEntryRecord
    federated_summary: ThresholdExchangeEntryRecord


@define(frozen=True, slots=True, kw_only=True)
class ModelExchangeRecord:
    field_width: str
    directions: tuple[str, ...]
    bytes_per_round_formula: str


@define(frozen=True, slots=True, kw_only=True)
class CheckpointStorageRecord:
    contents: tuple[str, ...]
    model_parameter_bytes_formula: str


@define(frozen=True, slots=True, kw_only=True)
class CommunicationEstimationContractRecord:
    estimate_basis: str
    field_encodings: Mapping[str, FieldEncodingRecord]
    threshold_exchange: ThresholdExchangeRecord
    candidate_grid_payload: str
    model_exchange: ModelExchangeRecord
    checkpoint_storage: CheckpointStorageRecord
    filename_match_is_not_lineage_evidence: bool
    frozen_artifacts_immutable: bool
    ambiguous_latest_reference: str


@define(frozen=True, slots=True, kw_only=True)
class BenignDecisionRateRecord:
    configured: bool
    value: float | None
    required_fields: tuple[str, ...]
    finite_value_validation: str
    non_negative_validation: str
    unavailable_behavior: str
    invented_rate_forbidden: bool


@define(frozen=True, slots=True, kw_only=True)
class OperationalInputsRecord:
    benign_decision_rate: BenignDecisionRateRecord


@define(frozen=True, slots=True, kw_only=True)
class NestedReplicatePolicyRecord:
    replicate_values_computed_first: bool
    summarized_within_seed_before_across_seed_inference: bool
    seed_level_statistic: str
    replicates_counted_as_independent_units: bool
    additional_required_replicate_statistic: str


@define(frozen=True, slots=True, kw_only=True)
class ResultTypeRecord:
    identifier: str
    permitted_evidence_roles: tuple[str, ...]


# --- Pure statistical procedure primitives (BCa/percentile bootstrap, Wilcoxon, Spearman, linear
# regression, Holm-Bonferroni correction) shared by every paired/temporal/association analysis.


class StatisticalProcedureError(ValueError):
    """A locked statistical procedure cannot produce a scientifically valid result."""


def matched_pairs_rank_biserial_correlation(left: Iterable[float], right: Iterable[float]) -> float:
    """Return the signed-rank effect size for paired observations, with average tie ranks."""
    differences = tuple(float(a) - float(b) for a, b in zip(left, right, strict=True))
    if not differences or not all(isfinite(value) for value in differences):
        raise StatisticalProcedureError("Rank-biserial correlation requires finite paired observations")
    nonzero = tuple(value for value in differences if not math.isclose(value, 0.0, abs_tol=0.0))
    if not nonzero:
        raise StatisticalProcedureError("Rank-biserial correlation is undefined when all paired differences are zero")
    ranks = _average_ranks(tuple(abs(value) for value in nonzero))
    positive = sum(rank for difference, rank in zip(nonzero, ranks, strict=True) if difference > 0.0)
    negative = sum(rank for difference, rank in zip(nonzero, ranks, strict=True) if difference < 0.0)
    return (positive - negative) / (positive + negative)


def holm_adjust_p_values(values: Iterable[float]) -> tuple[float, ...]:
    """Apply the Holm step-down correction and return values in the original order."""
    p_values = tuple(float(value) for value in values)
    if not all(isfinite(value) and 0.0 <= value <= 1.0 for value in p_values):
        raise StatisticalProcedureError("Holm correction requires finite p-values in [0, 1]")
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * len(p_values)
    previous = 0.0
    for rank, (index, p_value) in enumerate(ordered):
        corrected = min(1.0, (len(p_values) - rank) * p_value)
        previous = max(previous, corrected)
        adjusted[index] = previous
    return tuple(adjusted)


def _average_ranks(values: tuple[float, ...]) -> tuple[float, ...]:
    ranks = [0.0] * len(values)
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][1] == ordered[start][1]:
            end += 1
        average_rank = ((start + 1) + end) / 2.0
        for index, _ in ordered[start:end]:
            ranks[index] = average_rank
        start = end
    return tuple(ranks)


@define(frozen=True, slots=True, kw_only=True)
class ConfidenceInterval:
    lower_bound: float
    upper_bound: float
    confidence_level: Probability
    method: str

    def __attrs_post_init__(self) -> None:
        if self.lower_bound > self.upper_bound:
            raise ValueError("Lower bound cannot be greater than upper bound")

    @property
    def excludes_zero_positive(self) -> bool:
        return self.lower_bound > 0.0


@define(frozen=True, slots=True, kw_only=True)
class HypothesisTestResult:
    test_name: str
    statistic: float
    p_value: float
    degrees_of_freedom: float | None = None
    alternative: str = "two-sided"


@define(frozen=True, slots=True, kw_only=True)
class LinearRegressionResult:
    slope: float
    intercept: float
    standard_error: float
    r_squared: float
    leverage: tuple[float, ...]
    leave_one_out_slopes: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class PairedSeedDifferenceRecord:
    metric_id: MetricId
    policy_a_id: ThresholdPolicyId
    policy_b_id: ThresholdPolicyId
    mean_difference: float
    confidence_interval: ConfidenceInterval
    resample_count: int
    analysis_seed: Seed
    hypothesis_test: HypothesisTestResult | None = None
    effect_size: float | None = None


class StatisticalAnalysisUseCase:
    """Pure statistical analysis using native SciPy methods (BCa/percentile bootstrap, Wilcoxon,
    Spearman, linear regression). Held out of ``analysis/execution.py`` -- which every
    analysis-family module depends on for the ``StatisticalAnalysisStageHandler`` dispatch table --
    so that family modules can depend on this pure use case without importing the stage handler.
    """

    def __init__(self, profiles: TypedDomainRegistry[StatisticalProfileId, StatisticalProfileRecord]) -> None:
        self._profiles = profiles

    def analyze_paired_seed_differences(
        self,
        scores_policy_a: tuple[float, ...],
        scores_policy_b: tuple[float, ...],
        metric_name: str,
        policy_a_name: str,
        policy_b_name: str,
        statistical_profile_id: StatisticalProfileId,
        analysis_seed: Seed,
    ) -> PairedSeedDifferenceRecord:
        profile = self._profiles.get(statistical_profile_id)
        if (
            profile.method not in {"bca_bootstrap", "percentile_bootstrap"}
            or profile.resample_count is None
            or profile.confidence_level is None
        ):
            raise ValueError(
                f"Statistical profile '{statistical_profile_id.value}' is not an executable bootstrap profile"
            )
        arr_a = np.array(scores_policy_a, dtype=np.float64)
        arr_b = np.array(scores_policy_b, dtype=np.float64)
        if arr_a.shape != arr_b.shape:
            raise ValueError("Paired seed analysis requires equally sized policy score cohorts")
        diffs = arr_a - arr_b

        mean_diff = float(np.mean(diffs))
        ci = self._compute_bca_bootstrap_ci(
            diffs,
            resample_count=profile.resample_count.value,
            confidence_level=profile.confidence_level.value,
            analysis_seed=analysis_seed.value,
            method=profile.method,
        )
        test_res = self._compute_wilcoxon_signed_rank(arr_a, arr_b) if len(arr_a) >= 5 else None

        return PairedSeedDifferenceRecord(
            metric_id=MetricId(metric_name),
            policy_a_id=ThresholdPolicyId(policy_a_name),
            policy_b_id=ThresholdPolicyId(policy_b_name),
            mean_difference=mean_diff,
            confidence_interval=ci,
            hypothesis_test=test_res,
            effect_size=matched_pairs_rank_biserial_correlation(arr_a, arr_b) if test_res is not None else None,
            resample_count=profile.resample_count.value,
            analysis_seed=analysis_seed,
        )

    def analyze_association(
        self, predictor: tuple[float, ...], outcome: tuple[float, ...]
    ) -> tuple[HypothesisTestResult, LinearRegressionResult]:
        predictor_values = np.array(predictor, dtype=np.float64)
        outcome_values = np.array(outcome, dtype=np.float64)
        if len(predictor_values) < 3 or predictor_values.shape != outcome_values.shape:
            raise ValueError("Association analysis requires at least three paired finite observations")
        if not np.isfinite(predictor_values).all() or not np.isfinite(outcome_values).all():
            raise ValueError("Association analysis requires finite observations")
        return (
            self._compute_spearman(predictor_values, outcome_values),
            self._compute_linear_regression(predictor_values, outcome_values),
        )

    @staticmethod
    def _compute_wilcoxon_signed_rank(x: np.ndarray, y: np.ndarray) -> HypothesisTestResult:
        res = stats.wilcoxon(x, y, zero_method="wilcox", correction=True)
        statistic, p_value = cast("tuple[float, float]", res)
        return HypothesisTestResult(test_name="wilcoxon_signed_rank", statistic=float(statistic), p_value=float(p_value))

    @staticmethod
    def _compute_bca_bootstrap_ci(
        data: np.ndarray, resample_count: int, confidence_level: float, analysis_seed: int, method: str
    ) -> ConfidenceInterval:
        if method == "bca_bootstrap" and len(data) < 10:
            raise StatisticalProcedureError("BCa requires at least ten valid paired seed differences")
        if method == "percentile_bootstrap" and len(data) < 2:
            raise StatisticalProcedureError("Percentile bootstrap requires at least two valid paired seed differences")
        if not np.isfinite(data).all():
            raise StatisticalProcedureError("BCa requires finite paired seed differences")
        if math.isclose(float(np.ptp(data)), 0.0, abs_tol=0.0):
            raise StatisticalProcedureError("BCa is degenerate for identical paired seed differences")

        try:
            res = stats.bootstrap(
                (data,),
                np.mean,
                n_resamples=resample_count,
                confidence_level=confidence_level,
                method="BCa" if method == "bca_bootstrap" else "percentile",
                rng=np.random.default_rng(analysis_seed),
            )
        except ValueError as exc:
            raise StatisticalProcedureError(f"BCa failed: {exc}") from exc
        if not np.isfinite((res.confidence_interval.low, res.confidence_interval.high)).all():
            raise StatisticalProcedureError("BCa produced a non-finite confidence interval")
        return ConfidenceInterval(
            lower_bound=float(res.confidence_interval.low),
            upper_bound=float(res.confidence_interval.high),
            confidence_level=Probability(confidence_level),
            method=method,
        )

    @staticmethod
    def _compute_spearman(predictor: np.ndarray, outcome: np.ndarray) -> HypothesisTestResult:
        statistic, p_value = cast("tuple[float, float]", stats.spearmanr(predictor, outcome))
        if not np.isfinite((statistic, p_value)).all():
            raise StatisticalProcedureError("Spearman correlation is undefined for the supplied observations")
        return HypothesisTestResult(test_name="spearman_correlation", statistic=float(statistic), p_value=float(p_value))

    @staticmethod
    def _compute_linear_regression(predictor: np.ndarray, outcome: np.ndarray) -> LinearRegressionResult:
        slope, intercept, r_value, _, standard_error = cast(
            "tuple[float, float, float, float, float]", stats.linregress(predictor, outcome)
        )
        if not np.isfinite((slope, intercept, standard_error, r_value)).all():
            raise StatisticalProcedureError("Linear regression is undefined for the supplied observations")
        centered = predictor - np.mean(predictor)
        denominator = float(np.sum(centered**2))
        if math.isclose(denominator, 0.0, abs_tol=0.0):
            raise StatisticalProcedureError("Linear regression requires non-constant predictor observations")
        leverage = tuple(float((1.0 / len(predictor)) + (value**2 / denominator)) for value in centered)
        leave_one_out_slopes = tuple(
            cast(
                "tuple[float, float, float, float, float]",
                stats.linregress(np.delete(predictor, index), np.delete(outcome, index)),
            )[0]
            for index in range(len(predictor))
        )
        return LinearRegressionResult(
            slope=float(slope),
            intercept=float(intercept),
            standard_error=float(standard_error),
            r_squared=float(r_value**2),
            leverage=leverage,
            leave_one_out_slopes=leave_one_out_slopes,
        )


# --- Typed per-analysis-family RESULT hierarchy (section 12.2). Each record mirrors, field for
# field, the dict shape previously built ad hoc in ``application/analysis_stages.py``; the final
# JSON artifact payload is produced by ``analysis_result_to_payload`` below so the persisted
# on-disk schema is unchanged even though the in-memory computation is now fully typed.


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


@define(frozen=True, slots=True, kw_only=True)
class AbsorptionReference:
    experiment: ExperimentId
    analysis: str


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
