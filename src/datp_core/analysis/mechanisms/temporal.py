"""Temporal-recovery analysis."""

from __future__ import annotations

from attrs import define

from datp_core.analysis.comparisons.paired import evaluation_metric
from datp_core.analysis.enums import MetricIdentifier, TemporalOutcomeBand
from datp_core.analysis.errors import InvalidAnalysisConfigurationError
from datp_core.analysis.runtime.artifacts import AnalysisInputBundle
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.seeding import Seed
from datp_core.experiments import ExperimentRecord, TemporalRecoveryAnalysisRecord


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


def _policy_id(experiment: ExperimentRecord, label: str) -> str:
    """Return the threshold-policy ID string for the given evaluation label."""
    evaluation = next(item for item in experiment.evaluations if item.label == label)
    return evaluation.threshold_policy_id.value


def analyze_temporal_recovery(
    analysis: TemporalRecoveryAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    statistical_analysis: StatisticalAnalysisUseCase,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> TemporalRecoveryAnalysisResult:
    if analysis.primary_metric != MetricIdentifier.CV_FPR:
        raise InvalidAnalysisConfigurationError(
            f"Temporal analysis '{analysis.label}' has an unsupported primary metric"
        )

    def metric(label: str, seed: Seed) -> float:
        return evaluation_metric(
            config=config,
            artifacts=artifacts,
            inputs=inputs,
            experiment=experiment,
            seed=seed.value,
            label=label,
            metric=analysis.primary_metric,
            partition_condition=None,
            proximal_mu=None,
            ditto_weight=None,
            threshold_quantile=None,
            shrinkage_weight=None,
            calibration_sample_count=None,
        )

    static = tuple(metric(analysis.static_reference_evaluation, seed) for seed in seeds)
    frozen = tuple(metric(analysis.frozen_evaluation, seed) for seed in seeds)
    recalibrated = tuple(metric(analysis.recalibrated_evaluation, seed) for seed in seeds)
    drift = tuple(future - reference for future, reference in zip(frozen, static, strict=True))
    recovered = tuple(
        future - recalibrated_value for future, recalibrated_value in zip(frozen, recalibrated, strict=True)
    )
    record = statistical_analysis.analyze_paired_seed_differences(
        frozen,
        static,
        analysis.primary_metric,
        _policy_id(experiment,analysis.frozen_evaluation),
        _policy_id(experiment,analysis.static_reference_evaluation),
        analysis.statistical_profile,
        config.seed_cohorts.get(experiment.seed_cohort_id).bootstrap_analysis_seed,
    )
    meaningful = record.confidence_interval.lower_bound > 0.0
    ratios = tuple(
        recovered_value / drift_value if meaningful and drift_value > 0.0 else None
        for recovered_value, drift_value in zip(recovered, drift, strict=True)
    )
    defined = tuple(value for value in ratios if value is not None)
    band: str = TemporalOutcomeBand.NO_MEANINGFUL_DEGRADATION
    if meaningful:
        mean_ratio = sum(defined) / len(defined) if defined else None
        threshold = analysis.meaningful_recovery_threshold
        band = (
            TemporalOutcomeBand.MEANINGFUL_RECOVERY
            if mean_ratio is not None and mean_ratio >= threshold
            else TemporalOutcomeBand.INSUFFICIENT_RECOVERY
        )
    return TemporalRecoveryAnalysisResult(
        analysis_label=analysis.label,
        metric=analysis.primary_metric,
        static_reference_cv=static,
        frozen_future_cv=frozen,
        recalibrated_future_cv=recalibrated,
        drift_excess=drift,
        recovered_amount=recovered,
        recovery_ratio=ratios,
        meaningful_degradation=meaningful,
        drift_confidence_interval=(record.confidence_interval.lower_bound, record.confidence_interval.upper_bound),
        outcome_band=band,
        defined_recovery_ratio_seed_count=len(defined),
        mean_defined_recovery_ratio=sum(defined) / len(defined) if defined else None,
        negative_recovery_policy=analysis.negative_recovery_policy,
        chronology_unverifiable_policy=analysis.chronology_unverifiable_policy,
    )
