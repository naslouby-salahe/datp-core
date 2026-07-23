"""Temporal-recovery analysis: whether a one-shot recalibration recovers CV(FPR) drift accrued by
a frozen threshold, expressed as a specialized paired-seed comparison against the static baseline.
"""

from __future__ import annotations

from datp_core.analysis.models import StatisticalAnalysisUseCase, TemporalRecoveryAnalysisResult
from datp_core.analysis.paired import evaluation_metric, evaluation_policy
from datp_core.artifacts.models import ArtifactRepository
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.experiments.models import ExperimentRecord, TemporalRecoveryAnalysisRecord
from datp_core.pipeline.identifiers import RunId
from datp_core.pipeline.values import Seed


def analyze_temporal_recovery(
    analysis: TemporalRecoveryAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    statistical_analysis: StatisticalAnalysisUseCase,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> TemporalRecoveryAnalysisResult:
    if analysis.primary_metric != "cv_fpr":
        raise ValueError(f"Temporal analysis '{analysis.label}' has an unsupported primary metric")

    def metric(label: str, seed: Seed) -> float:
        return evaluation_metric(
            config=config,
            repository=repository,
            experiment=experiment,
            seed=seed.value,
            label=label,
            metric=analysis.primary_metric,
            run_id=run_id,
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
        evaluation_policy(experiment, analysis.frozen_evaluation),
        evaluation_policy(experiment, analysis.static_reference_evaluation),
        analysis.statistical_profile,
        config.seed_cohorts.get(experiment.seed_cohort_id).bootstrap_analysis_seed,
    )
    meaningful = record.confidence_interval.lower_bound > 0.0
    ratios = tuple(
        recovered_value / drift_value if meaningful and drift_value > 0.0 else None
        for recovered_value, drift_value in zip(recovered, drift, strict=True)
    )
    defined = tuple(value for value in ratios if value is not None)
    band = "no_meaningful_degradation"
    if meaningful:
        mean_ratio = sum(defined) / len(defined) if defined else None
        threshold = analysis.meaningful_recovery_threshold
        band = "meaningful_recovery" if mean_ratio is not None and mean_ratio >= threshold else "insufficient_recovery"
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


__all__ = ["analyze_temporal_recovery"]
