"""Result records for paired-threshold comparison, metric association, recovery fraction, and
absorption analyses."""

from __future__ import annotations

from attrs import define

from datp_core.analysis.statistics.models import ConfidenceInterval


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
class RecoveryFractionAnalysisResult:
    analysis_label: str
    formula: str
    undefined_denominator_behavior: str
    per_seed_recovery_fraction: tuple[float | None, ...]
    defined_seed_count: int
    mean_defined_recovery_fraction: float | None


@define(frozen=True, slots=True, kw_only=True)
class SeedRatioResult:
    """Generic seed-indexed ratio-of-differences result, produced by absorption analyses."""

    analysis_label: str
    formula: str
    undefined_denominator_behavior: str
    per_seed_ratio: tuple[float | None, ...]
    defined_seed_count: int
    mean_defined_ratio: float | None
    ratio_of_seed_means: float | None


AbsorptionAnalysisResult = SeedRatioResult


__all__ = [
    "AbsorptionAnalysisResult",
    "AssociationCorrelationResult",
    "AssociationObservationRecord",
    "AssociationRegressionResult",
    "MetricAssociationAnalysisResult",
    "PairedThresholdAnalysisResult",
    "RecoveryFractionAnalysisResult",
    "SeedRatioResult",
]
