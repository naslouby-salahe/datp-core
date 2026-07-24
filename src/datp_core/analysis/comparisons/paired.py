"""Paired-threshold analysis: the core seed-paired statistical comparison every other analysis
family builds on."""

from __future__ import annotations

import math
from collections.abc import Mapping

import polars as pl

from datp_core.analysis.artifact_access.metric_query import evaluation_policy_id as evaluation_policy
from datp_core.analysis.artifact_access.metric_query import experiment_evaluation
from datp_core.analysis.artifact_access.reader import read_parquet_frame
from datp_core.analysis.comparisons.models import PairedThresholdAnalysisResult
from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.artifacts.models import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.contracts.frames import validate_client_metric_frame
from datp_core.core.identifiers import RunId
from datp_core.core.values import Seed
from datp_core.evaluation.models import MetricStatus, calculate_fpr_dispersion
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.models import ExperimentRecord, PairedThresholdAnalysisRecord
from datp_core.pipeline.models import StageJobContext


def analyze_paired(
    analysis: PairedThresholdAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    statistical_analysis: StatisticalAnalysisUseCase,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
    partition_condition: str | None,
    proximal_mu: float | None,
    ditto_weight: float | None,
    threshold_quantile: float | None,
    shrinkage_weight: float | None,
    calibration_sample_count: int | None,
) -> PairedThresholdAnalysisResult:
    left = tuple(
        evaluation_metric(
            config=config,
            repository=repository,
            experiment=experiment,
            seed=seed.value,
            label=analysis.first_evaluation,
            metric=analysis.primary_metric,
            run_id=run_id,
            partition_condition=partition_condition,
            proximal_mu=proximal_mu,
            ditto_weight=ditto_weight,
            threshold_quantile=threshold_quantile,
            shrinkage_weight=shrinkage_weight,
            calibration_sample_count=calibration_sample_count,
        )
        for seed in seeds
    )
    right = tuple(
        evaluation_metric(
            config=config,
            repository=repository,
            experiment=experiment,
            seed=seed.value,
            label=analysis.second_evaluation,
            metric=analysis.primary_metric,
            run_id=run_id,
            partition_condition=partition_condition,
            proximal_mu=proximal_mu,
            ditto_weight=ditto_weight,
            threshold_quantile=threshold_quantile,
            shrinkage_weight=shrinkage_weight,
            calibration_sample_count=calibration_sample_count,
        )
        for seed in seeds
    )
    record = statistical_analysis.analyze_paired_seed_differences(
        left,
        right,
        analysis.primary_metric,
        evaluation_policy(experiment, analysis.first_evaluation),
        evaluation_policy(experiment, analysis.second_evaluation),
        analysis.statistical_profile,
        config.seed_cohorts.get(experiment.seed_cohort_id).bootstrap_analysis_seed,
    )
    differences = tuple(first - second for first, second in zip(left, right, strict=True))
    return PairedThresholdAnalysisResult(
        analysis_label=analysis.label,
        metric=record.metric_id.value,
        first_threshold_policy=evaluation_policy(experiment, analysis.first_evaluation),
        second_threshold_policy=evaluation_policy(experiment, analysis.second_evaluation),
        training_seeds=tuple(seed.value for seed in seeds),
        first_seed_values=left,
        second_seed_values=right,
        first_mean=sum(left) / len(left),
        second_mean=sum(right) / len(right),
        mean_difference=record.mean_difference,
        confidence_interval=record.confidence_interval,
        p_value=None if record.hypothesis_test is None else record.hypothesis_test.p_value,
        rank_biserial=record.effect_size,
        resample_count=record.resample_count,
        analysis_seed=record.analysis_seed.value,
        seed_differences=differences,
        sign_consistency=sum(value > 0.0 for value in differences) / len(differences),
        zero_difference_count=sum(math.isclose(value, 0.0, abs_tol=0.0) for value in differences),
        negative_difference_count=sum(value < 0.0 for value in differences),
        partition_condition=partition_condition,
        federated_proximal_mu=proximal_mu,
        ditto_proximal_weight=ditto_weight,
        threshold_quantile=threshold_quantile,
        shrinkage_weight=shrinkage_weight,
        calibration_sample_count=calibration_sample_count,
    )


def evaluation_metric(
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seed: int,
    label: str,
    metric: str,
    run_id: RunId,
    partition_condition: str | None,
    proximal_mu: float | None,
    ditto_weight: float | None,
    threshold_quantile: float | None,
    shrinkage_weight: float | None,
    calibration_sample_count: int | None,
) -> float:
    if metric != "cv_fpr":
        raise ValueError(f"Statistical execution does not support configured metric '{metric}'")
    evaluation = experiment_evaluation(experiment, label)
    overrides = evaluation.overrides or {}
    quantile_override = overrides.get("quantile")
    shrinkage_override = overrides.get("shrinkage_weight")
    policy = config.threshold_policies.get(evaluation.threshold_policy_id)
    quantile = threshold_quantile if isinstance(quantile_override, Mapping) else getattr(policy, "quantile", None)
    if not isinstance(quantile, float):
        raise ValueError(f"Evaluation '{label}' does not bind a quantile threshold policy")
    definition = config.metric_definitions.cross_client_aggregation.cv_fpr
    if definition.near_zero_mean_threshold_formula != "0.10 * (1 - evaluated_threshold_policy_quantile)":
        raise ValueError("CV(FPR) near-zero threshold formula is not the configured roadmap formula")
    if definition.near_zero_mean_threshold_factor is None:
        raise ValueError("CV(FPR) near-zero threshold factor is not configured")
    instability_factor = definition.near_zero_mean_threshold_factor
    replicates: tuple[int | None, ...] = (None,)
    if calibration_sample_count is not None:
        subset = experiment.calibration_subset
        if subset is None:
            raise ValueError("Calibration sample count is invalid for an experiment without a subset contract")
        replicates = tuple(range(subset.replicate_count.value))
    values: list[float] = []
    for replicate in replicates:
        context = StageJobContext(
            experiment_id=experiment.identifier,
            seed=seed,
            partition_condition=partition_condition,
            federated_proximal_mu=proximal_mu,
            ditto_proximal_weight=ditto_weight,
            threshold_quantile=threshold_quantile if isinstance(quantile_override, Mapping) else None,
            shrinkage_weight=shrinkage_weight if isinstance(shrinkage_override, Mapping) else None,
            calibration_sample_count=calibration_sample_count,
            calibration_replicate=replicate,
            evaluation_label=label,
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
        )
        values.append(
            _read_cv_fpr_metric(
                context=context,
                repository=repository,
                run_id=run_id,
                seed=seed,
                label=label,
                quantile=quantile,
                instability_factor=instability_factor,
            )
        )
    return sum(values) / len(values)


def _read_cv_fpr_metric(
    *,
    context: StageJobContext,
    repository: ArtifactRepository,
    run_id: RunId,
    seed: int,
    label: str,
    quantile: float,
    instability_factor: float,
) -> float:
    frame = validate_client_metric_frame(
        read_parquet_frame(
            repository,
            run_id,
            IdentityBuilder.evaluation_job_id(context),
            missing_message=f"Evaluation artifact is unavailable for seed {seed}, label '{label}'",
        )
    )
    fprs = tuple(
        float(value)
        for value in frame.filter(pl.col("false_positive_rate_status") == "available")["false_positive_rate"].to_list()
    )
    dispersion = calculate_fpr_dispersion(fprs, cv_instability_threshold=instability_factor * (1.0 - quantile))
    if dispersion.coefficient_of_variation.status is MetricStatus.UNDEFINED_ZERO_DENOMINATOR:
        raise ValueError("Configured CV(FPR) is unavailable for paired statistical analysis")
    assert dispersion.coefficient_of_variation.value is not None
    return dispersion.coefficient_of_variation.value


__all__ = ["analyze_paired", "evaluation_metric", "evaluation_policy"]
