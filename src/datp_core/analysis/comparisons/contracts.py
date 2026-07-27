"""Comparison-specific analysis contracts."""

from __future__ import annotations

from typing import Literal

from datp_core.analysis._base import ConfidenceInterval, FrozenModel
from datp_core.analysis.enums import (
    AnalysisResultKind,
    AnchorCheckIdentifier,
    AnchorComparisonMode,
    UndefinedDenominatorBehavior,
)
from datp_core.core.identifiers import AnalysisLabel, MetricId, PartitionConditionId, ThresholdPolicyId
from datp_core.core.seeding import Seed


class PairedThresholdAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.PAIRED_THRESHOLD] = AnalysisResultKind.PAIRED_THRESHOLD
    payload_version: Literal[1] = 1
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


class AssociationCorrelationResult(FrozenModel):
    coefficient: float
    p_value: float


class AssociationRegressionResult(FrozenModel):
    coefficient: float
    intercept: float
    standard_error: float
    r_squared: float
    leverage: tuple[float, ...]
    leave_one_out_slopes: tuple[float, ...]


class AssociationObservationRecord(FrozenModel):
    partition_condition: PartitionConditionId
    seed: Seed
    pairwise_js_divergence: float
    cv_fpr_delta: float


class MetricAssociationAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.METRIC_ASSOCIATION] = AnalysisResultKind.METRIC_ASSOCIATION
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    interpretation_constraint: str
    spearman: AssociationCorrelationResult
    linear_regression: AssociationRegressionResult
    observations: tuple[AssociationObservationRecord, ...]


class AbsorptionAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.ABSORPTION] = AnalysisResultKind.ABSORPTION
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    formula: str
    undefined_denominator_behavior: UndefinedDenominatorBehavior
    per_seed_ratio: tuple[float | None, ...]
    defined_seed_count: int
    mean_defined_ratio: float | None
    ratio_of_seed_means: float | None


class RecoveryFractionAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.RECOVERY_FRACTION] = AnalysisResultKind.RECOVERY_FRACTION
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    formula: str
    undefined_denominator_behavior: UndefinedDenominatorBehavior
    per_seed_recovery_fraction: tuple[float | None, ...]
    defined_seed_count: int
    mean_defined_recovery_fraction: float | None


class AnchorHistoricalReference(FrozenModel):
    delta: float
    lower_bound: float
    upper_bound: float
    interval_width: float


class AnchorEquivalenceChecks(FrozenModel):
    positive_reproduced_delta: bool
    reproduced_estimate_within_historical_interval: bool
    overlapping_confidence_intervals: bool
    no_material_movement_toward_zero: bool
    reproduced_interval_width_at_most_1_20x_historical_width: bool
    verified_configuration_and_provenance: bool


class AnchorEquivalenceAnalysisResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.ANCHOR_EQUIVALENCE] = AnalysisResultKind.ANCHOR_EQUIVALENCE
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    comparison_mode: AnchorComparisonMode
    source_analysis: AnalysisLabel
    passed: bool
    failure_reasons: tuple[AnchorCheckIdentifier, ...]
    checks: AnchorEquivalenceChecks
    reproduced_delta: float
    reproduced_confidence_interval: tuple[float, float]
    historical_reference: AnchorHistoricalReference
