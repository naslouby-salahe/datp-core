"""Paired-threshold analysis: core seed-paired statistical comparison."""

from __future__ import annotations

from collections.abc import Mapping

import polars as pl

from datp_core.analysis.contracts import PairedThresholdAnalysisResult, QuantileThresholdPolicy
from datp_core.analysis.enums import FormulaIdentifier, MetricIdentifier
from datp_core.analysis.errors import (
    InvalidAnalysisConfigurationError,
    ScientificContractViolationError,
    StatisticalProcedureError,
)
from datp_core.analysis.runtime.artifacts import AnalysisInputBundle
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.artifacts.schemas.columns import MetricColumn
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.seeding import Seed
from datp_core.evaluation import MetricStatus, calculate_fpr_dispersion
from datp_core.experiments import ExperimentRecord, PairedThresholdAnalysisRecord
from datp_core.pipeline.stages.context import StageJobContext


def analyze_paired(
    analysis: PairedThresholdAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    statistical_analysis: StatisticalAnalysisUseCase,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    partition_condition: str | None,
    proximal_mu: float | None,
    ditto_weight: float | None,
    threshold_quantile: float | None,
    shrinkage_weight: float | None,
    calibration_sample_count: int | None,
    context: AnalysisExecutionContext | None = None,
) -> PairedThresholdAnalysisResult:
    left = tuple(
        evaluation_metric(
            config=config,
            artifacts=artifacts,
            inputs=inputs,
            experiment=experiment,
            seed=seed.value,
            label=analysis.first_evaluation,
            metric=analysis.primary_metric,
            partition_condition=partition_condition,
            proximal_mu=proximal_mu,
            ditto_weight=ditto_weight,
            threshold_quantile=threshold_quantile,
            shrinkage_weight=shrinkage_weight,
            calibration_sample_count=calibration_sample_count,
            context=context,
        )
        for seed in seeds
    )
    right = tuple(
        evaluation_metric(
            config=config,
            artifacts=artifacts,
            inputs=inputs,
            experiment=experiment,
            seed=seed.value,
            label=analysis.second_evaluation,
            metric=analysis.primary_metric,
            partition_condition=partition_condition,
            proximal_mu=proximal_mu,
            ditto_weight=ditto_weight,
            threshold_quantile=threshold_quantile,
            shrinkage_weight=shrinkage_weight,
            calibration_sample_count=calibration_sample_count,
            context=context,
        )
        for seed in seeds
    )
    first_policy_id = (
        context.threshold_policy_id(analysis.first_evaluation).value
        if context is not None
        else next(
            item for item in experiment.evaluations if item.label == analysis.first_evaluation
        ).threshold_policy_id.value
    )
    second_policy_id = (
        context.threshold_policy_id(analysis.second_evaluation).value
        if context is not None
        else next(
            item for item in experiment.evaluations if item.label == analysis.second_evaluation
        ).threshold_policy_id.value
    )
    record = statistical_analysis.analyze_paired_seed_differences(
        left,
        right,
        analysis.primary_metric,
        first_policy_id,
        second_policy_id,
        analysis.statistical_profile,
        config.seed_cohorts.get(experiment.seed_cohort_id).bootstrap_analysis_seed,
    )
    differences = tuple(first - second for first, second in zip(left, right, strict=True))
    return PairedThresholdAnalysisResult(
        analysis_label=analysis.label,
        metric=record.metric_id.value,
        first_threshold_policy=first_policy_id,
        second_threshold_policy=second_policy_id,
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
        zero_difference_count=sum(value == 0.0 for value in differences),
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
    artifacts: AnalysisArtifactRepository,
    inputs,
    experiment: ExperimentRecord,
    seed: int,
    label: str,
    metric: str,
    partition_condition: str | None,
    proximal_mu: float | None,
    ditto_weight: float | None,
    threshold_quantile: float | None,
    shrinkage_weight: float | None,
    calibration_sample_count: int | None,
    context: AnalysisExecutionContext | None = None,
) -> float:
    if metric != MetricIdentifier.CV_FPR:
        raise InvalidAnalysisConfigurationError(
            f"Statistical execution does not support configured metric '{metric}'"
        )
    if context is not None:
        evaluation = context.evaluation(label)
    else:
        evaluation = next(item for item in experiment.evaluations if item.label == label)
    overrides = evaluation.overrides or {}
    quantile_override = overrides.get("quantile")
    shrinkage_override = overrides.get("shrinkage_weight")
    if context is not None:
        has_quantile_override = isinstance(quantile_override, Mapping)
        quantile = threshold_quantile if has_quantile_override else context.quantile_for_evaluation(label)
    else:
        policy = config.threshold_policies.get(evaluation.threshold_policy_id)
        quantile = (
            threshold_quantile
            if isinstance(quantile_override, Mapping)
            else (policy.quantile if isinstance(policy, QuantileThresholdPolicy) else None)
        )
        if not isinstance(quantile, float):
            raise InvalidAnalysisConfigurationError(
                f"Evaluation '{label}' does not bind a quantile threshold policy"
            )
    definition = config.metric_definitions.cross_client_aggregation.cv_fpr
    if definition.near_zero_mean_threshold_formula != FormulaIdentifier.CV_FPR_NEAR_ZERO_THRESHOLD:
        raise ScientificContractViolationError(
            "CV(FPR) near-zero threshold formula is not the configured roadmap formula"
        )
    if definition.near_zero_mean_threshold_factor is None:
        raise InvalidAnalysisConfigurationError("CV(FPR) near-zero threshold factor is not configured")
    instability_factor = definition.near_zero_mean_threshold_factor
    replicates: tuple[int | None, ...] = (None,)
    if calibration_sample_count is not None:
        subset = experiment.calibration_subset
        if subset is None:
            raise InvalidAnalysisConfigurationError(
                "Calibration sample count is invalid for an experiment without a subset contract"
            )
        replicates = tuple(range(subset.replicate_count.value))
    values: list[float] = []
    for replicate in replicates:
        if context is not None:
            stage_ctx = context.evaluation_context(
                label, seed,
                partition_condition=partition_condition,
                proximal_mu=proximal_mu,
                ditto_weight=ditto_weight,
                threshold_quantile=threshold_quantile if isinstance(quantile_override, Mapping) else None,
                shrinkage_weight=shrinkage_weight if isinstance(shrinkage_override, Mapping) else None,
                calibration_sample_count=calibration_sample_count,
                calibration_replicate=replicate,
            )
        else:
            stage_ctx = StageJobContext(
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
        if not isinstance(quantile, float):
            raise InvalidAnalysisConfigurationError(
                f"Evaluation '{label}' requires a numeric quantile, got {quantile!r}"
            )
        values.append(
            _read_cv_fpr_metric(
                context=stage_ctx,
                artifacts=artifacts,
                inputs=inputs,
                quantile=quantile,
                instability_factor=instability_factor,
            )
        )
    return sum(values) / len(values)


def _read_cv_fpr_metric(
    *,
    context: StageJobContext,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    quantile: float,
    instability_factor: float,
) -> float:
    relative_path = inputs.evaluation_metrics(context)
    frame = artifacts.client_metric_frame(relative_path)
    fprs = tuple(
        float(value)
        for value in frame.filter(
            pl.col(MetricColumn.FALSE_POSITIVE_RATE_STATUS.value) == MetricStatus.AVAILABLE
        )[MetricColumn.FALSE_POSITIVE_RATE.value].to_list()
    )
    dispersion = calculate_fpr_dispersion(fprs, cv_instability_threshold=instability_factor * (1.0 - quantile))
    if dispersion.coefficient_of_variation.status is not MetricStatus.AVAILABLE:
        raise StatisticalProcedureError(
            f"Configured CV(FPR) is unavailable for paired statistical analysis: "
            f"{dispersion.coefficient_of_variation.status.value}"
        )
    if dispersion.coefficient_of_variation.value is None:
        raise StatisticalProcedureError(
            "CV(FPR) coefficient of variation is unexpectedly None"
        )
    return dispersion.coefficient_of_variation.value


