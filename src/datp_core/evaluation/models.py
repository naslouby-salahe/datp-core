"""Domain models for operating point evaluation, confusion matrices, and metrics."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from math import isfinite, log, sqrt
from statistics import mean

from attrs import define

from datp_core.core.identifiers import ClientId, MetricBundleId
from datp_core.core.values import linear_quantile


@define(frozen=True, slots=True, kw_only=True)
class MetricFormulaRecord:
    """Reusable leaf descriptor for a single metric definition (superset of all metric keys)."""

    formula: str | None
    unit: str | None
    direction: str | None
    zero_denominator: str | None
    requires: tuple[str, ...] | None
    missing_class_behavior: str | None
    requires_both_classes: bool | None
    role: str | None
    invariance_check: str | None
    quantile_estimator: str | None
    zero_sum_behavior: str | None
    zero_oracle_behavior: str | None
    zero_mean_behavior: str | None
    denominator_stabilizer: str | None
    near_zero_mean_threshold_formula: str | None
    near_zero_mean_behavior: str | None
    near_zero_mean_threshold_factor: float | None
    minimum_client_count: int | None
    weighting: str | None
    comparison_unit: str | None


@define(frozen=True, slots=True, kw_only=True)
class CrossClientAggregationRecord:
    mean_fpr: MetricFormulaRecord
    standard_deviation_ddof: int
    cv_fpr: MetricFormulaRecord
    cv_tpr: MetricFormulaRecord
    iqr_fpr: MetricFormulaRecord
    fpr_range: MetricFormulaRecord
    worst_client_fpr: MetricFormulaRecord
    p10_macro_f1: MetricFormulaRecord
    worst_client_ba: MetricFormulaRecord
    jain_index: MetricFormulaRecord
    gini_coefficient: MetricFormulaRecord


@define(frozen=True, slots=True, kw_only=True)
class ThresholdEstimationMetricsRecord:
    absolute_threshold_error: MetricFormulaRecord
    relative_threshold_error: MetricFormulaRecord
    oracle_definition: str
    target_exceedance: MetricFormulaRecord
    signed_attainment_error: MetricFormulaRecord
    absolute_attainment_error: MetricFormulaRecord
    threshold_dispersion: MetricFormulaRecord
    threshold_variance_across_replicates: MetricFormulaRecord


@define(frozen=True, slots=True, kw_only=True)
class JsDivergenceRecord:
    definition: str
    histogram_bins: int
    binning_range: str
    binning_edges: str
    logarithm_base: int
    empty_bin_handling: str
    pairwise_aggregation: str
    unit: str
    direction: str
    minimum_client_count: int


@define(frozen=True, slots=True, kw_only=True)
class HeterogeneityDiagnosticsRecord:
    pairwise_js_divergence: JsDivergenceRecord


@define(frozen=True, slots=True, kw_only=True)
class ClusterDiagnosticsRecord:
    adjusted_rand_index: MetricFormulaRecord
    within_cluster_dispersion: MetricFormulaRecord
    across_cluster_dispersion: MetricFormulaRecord


@define(frozen=True, slots=True, kw_only=True)
class PrecisionPolicyRecord:
    computation: str
    rounding: str


@define(frozen=True, slots=True, kw_only=True)
class MetricDefinitionsRecord:
    prediction_rule: str
    per_client_before_aggregation: bool
    test_rows_only: bool
    fpr: MetricFormulaRecord
    tpr: MetricFormulaRecord
    balanced_accuracy: MetricFormulaRecord
    macro_f1: MetricFormulaRecord
    auroc: MetricFormulaRecord
    cross_client_aggregation: CrossClientAggregationRecord
    threshold_estimation: ThresholdEstimationMetricsRecord
    heterogeneity_diagnostics: HeterogeneityDiagnosticsRecord
    cluster_diagnostics: ClusterDiagnosticsRecord
    precision_policy: PrecisionPolicyRecord
    metric_statuses: tuple[str, ...]
    forbidden_substitutions: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class EvaluationResultContractRecord:
    per_evaluation_result_type: str
    per_evaluation_eligibility_result_type: str
    per_evaluation_required_records: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class MetricBundleRecord:
    """Pure resolved metric bundle, referenced by PopulationRecord.metric_bundle_id."""

    identifier: MetricBundleId
    metrics: tuple[str, ...]
    cross_client_aggregation: str | None
    primary_dispersion_metric: str | None
    model_quality_control: str | None
    excludes_ineligible_clients: bool | None
    requires_attack_evaluable_clients: bool | None


class MetricStatus(Enum):
    AVAILABLE = "available"
    UNDEFINED_ZERO_DENOMINATOR = "undefined_zero_denominator"
    UNDEFINED_NEAR_ZERO_DENOMINATOR = "undefined_near_zero_denominator"
    UNAVAILABLE_MISSING_BENIGN_CLASS = "unavailable_missing_benign_class"
    UNAVAILABLE_MISSING_ATTACK_CLASS = "unavailable_missing_attack_class"
    UNAVAILABLE_INVALID_ATTACK_ASSIGNMENT = "unavailable_invalid_attack_assignment"
    UNAVAILABLE_INELIGIBLE_CLIENT = "unavailable_ineligible_client"
    UNAVAILABLE_UNSUPPORTED_REGIME = "unavailable_unsupported_regime"
    FAILED_INVALID_ARTIFACT = "failed_invalid_artifact"
    FAILED_STATISTICAL_PROCEDURE = "failed_statistical_procedure"


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricValue:
    value: float | None
    status: MetricStatus

    def __post_init__(self) -> None:
        if self.status is MetricStatus.AVAILABLE and self.value is None:
            raise ValueError("An available metric must have a value")
        valid_value_statuses = {MetricStatus.AVAILABLE, MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR}
        if self.status not in valid_value_statuses and self.value is not None:
            raise ValueError("An unavailable metric must not have a substitute value")

    @classmethod
    def available(cls, value: float) -> MetricValue:
        return cls(value=value, status=MetricStatus.AVAILABLE)

    @classmethod
    def unavailable(cls, status: MetricStatus) -> MetricValue:
        if status is MetricStatus.AVAILABLE:
            raise ValueError("Use available() for an available metric")
        return cls(value=None, status=status)


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientConfusionMatrix:
    client_id: ClientId
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int

    def __post_init__(self) -> None:
        if any(v < 0 for v in (self.true_positives, self.false_positives, self.true_negatives, self.false_negatives)):
            raise ValueError("Confusion matrix counts must be non-negative")

    @property
    def false_positive_rate(self) -> MetricValue:
        total_negatives = self.false_positives + self.true_negatives
        if total_negatives == 0:
            return MetricValue.unavailable(MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS)
        return MetricValue.available(self.false_positives / total_negatives)

    @property
    def true_positive_rate(self) -> MetricValue:
        total_positives = self.true_positives + self.false_negatives
        if total_positives == 0:
            return MetricValue.unavailable(MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS)
        return MetricValue.available(self.true_positives / total_positives)

    @property
    def balanced_accuracy(self) -> MetricValue:
        fpr = self.false_positive_rate
        tpr = self.true_positive_rate
        if fpr.status is not MetricStatus.AVAILABLE:
            return MetricValue.unavailable(fpr.status)
        if tpr.status is not MetricStatus.AVAILABLE:
            return MetricValue.unavailable(tpr.status)
        assert fpr.value is not None and tpr.value is not None
        return MetricValue.available((tpr.value + (1.0 - fpr.value)) / 2.0)

    @property
    def macro_f1(self) -> MetricValue:
        benign_support = self.true_negatives + self.false_positives
        attack_support = self.true_positives + self.false_negatives
        benign_denominator = (2 * self.true_negatives) + self.false_positives + self.false_negatives
        attack_denominator = (2 * self.true_positives) + self.false_positives + self.false_negatives
        if benign_support == 0:
            return MetricValue.unavailable(MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS)
        if attack_support == 0:
            return MetricValue.unavailable(MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS)
        if benign_denominator == 0 or attack_denominator == 0:
            return MetricValue.unavailable(MetricStatus.UNDEFINED_ZERO_DENOMINATOR)
        benign_f1 = (2 * self.true_negatives) / benign_denominator
        attack_f1 = (2 * self.true_positives) / attack_denominator
        return MetricValue.available((benign_f1 + attack_f1) / 2.0)


@dataclass(frozen=True, slots=True, kw_only=True)
class FprDispersion:
    mean_fpr: MetricValue
    standard_deviation: MetricValue
    coefficient_of_variation: MetricValue
    iqr: MetricValue
    value_range: MetricValue
    worst_fpr: MetricValue


def calculate_fpr_dispersion(values: Iterable[float], *, cv_instability_threshold: float) -> FprDispersion:
    """Calculate unweighted cross-client FPR dispersion with explicit undefined states."""
    fprs = tuple(values)
    if not fprs:
        unavailable = MetricValue.unavailable(MetricStatus.UNDEFINED_ZERO_DENOMINATOR)
        return FprDispersion(
            mean_fpr=unavailable,
            standard_deviation=unavailable,
            coefficient_of_variation=unavailable,
            iqr=unavailable,
            value_range=unavailable,
            worst_fpr=unavailable,
        )
    if cv_instability_threshold <= 0.0:
        raise ValueError("cv_instability_threshold must be positive")
    if any(value < 0.0 or value > 1.0 for value in fprs):
        raise ValueError("FPR values must be in [0, 1]")
    average = mean(fprs)
    standard_deviation = sqrt(sum((value - average) ** 2 for value in fprs) / len(fprs))
    q25 = linear_quantile(fprs, 0.25)
    q75 = linear_quantile(fprs, 0.75)
    if math.isclose(average, 0.0, abs_tol=0.0):
        cv = MetricValue.unavailable(MetricStatus.UNDEFINED_ZERO_DENOMINATOR)
    elif average < cv_instability_threshold:
        cv = MetricValue(value=standard_deviation / average, status=MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR)
    else:
        cv = MetricValue.available(standard_deviation / average)
    stable = MetricValue.available
    return FprDispersion(
        mean_fpr=stable(average),
        standard_deviation=stable(standard_deviation),
        coefficient_of_variation=cv,
        iqr=stable(q75 - q25),
        value_range=stable(max(fprs) - min(fprs)),
        worst_fpr=stable(max(fprs)),
    )


def assert_auroc_invariant(values: Iterable[float], *, tolerance: float) -> None:
    scores = tuple(values)
    if tolerance < 0.0:
        raise ValueError("tolerance must be non-negative")
    if scores and max(scores) - min(scores) > tolerance:
        raise ValueError("AUROC must be invariant across fixed-score threshold policies")


def calculate_pairwise_js_divergence(
    client_scores: Sequence[tuple[ClientId, tuple[float, ...]]], *, histogram_bins: int, logarithm_base: int
) -> float:
    """Return the configured mean pairwise JS divergence for benign client score distributions."""
    if histogram_bins < 1 or logarithm_base < 2:
        raise ValueError("Pairwise JS divergence requires configured positive bins and logarithm base >= 2")
    if len(client_scores) < 2:
        raise ValueError("Pairwise JS divergence requires at least two clients")
    if any(not scores for _, scores in client_scores):
        raise ValueError("Pairwise JS divergence requires non-empty benign score distributions")
    values = tuple(score for _, scores in client_scores for score in scores)
    if not all(isfinite(score) and score >= 0.0 for score in values):
        raise ValueError("Pairwise JS divergence requires finite non-negative scores")
    lower, upper = min(values), max(values)

    def histogram(scores: tuple[float, ...]) -> tuple[float, ...]:
        counts = [0] * histogram_bins
        for score in scores:
            index = (
                0
                if lower == upper
                else min(int((score - lower) / (upper - lower) * histogram_bins), histogram_bins - 1)
            )
            counts[index] += 1
        return tuple(count / len(scores) for count in counts)

    distributions = tuple(histogram(scores) for _, scores in client_scores)
    divergences = []
    for left_index, left in enumerate(distributions):
        for right in distributions[left_index + 1 :]:
            midpoint = tuple((first + second) / 2.0 for first, second in zip(left, right, strict=True))
            divergences.append(
                sum(
                    probability * log(probability / midpoint[index], logarithm_base)
                    for index, probability in enumerate(left)
                    if probability > 0.0
                )
                / 2.0
                + sum(
                    probability * log(probability / midpoint[index], logarithm_base)
                    for index, probability in enumerate(right)
                    if probability > 0.0
                )
                / 2.0
            )
    return mean(divergences)
