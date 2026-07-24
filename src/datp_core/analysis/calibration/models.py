"""Result records for conformal coverage, quantile estimation, and threshold-stability analyses."""

from __future__ import annotations

from collections.abc import Mapping

from attrs import define


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


__all__ = [
    "ConformalClientCoverageRecord",
    "ConformalCoverageAnalysisResult",
    "ConformalSeedCoverageResult",
    "QuantileEstimationAnalysisResult",
    "QuantileEstimationClientResult",
    "QuantileEstimationEvaluationResult",
    "QuantileEstimationSeedResult",
    "ThresholdStabilityAnalysisResult",
    "ThresholdStabilitySeedResult",
]
