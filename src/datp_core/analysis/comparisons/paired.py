"""Paired-threshold analysis: core seed-paired statistical comparison."""

from __future__ import annotations

from collections.abc import Mapping

import polars as pl

from datp_core.analysis.contracts import (
    PairedAnalysisCell,
    PairedThresholdAnalysisResult,
)
from datp_core.analysis.enums import FormulaIdentifier, MetricIdentifier
from datp_core.analysis.errors import (
    InvalidAnalysisConfigurationError,
    ScientificContractViolationError,
    StatisticalProcedureError,
)
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.runner import run_analysis
from datp_core.artifacts.schemas.columns import MetricColumn
from datp_core.core.identifiers import AnalysisLabel, EvaluationLabel, MetricId
from datp_core.core.seeding import Seed
from datp_core.evaluation import MetricStatus, calculate_fpr_dispersion
from datp_core.experiments import PairedThresholdAnalysisRecord


@run_analysis.register
def analyze_paired(
    specification: PairedThresholdAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[PairedThresholdAnalysisResult, ...]:
    """Execute paired-threshold analysis across experiment seeds."""
    eval_a = EvaluationLabel(specification.first_evaluation)
    eval_b = EvaluationLabel(specification.second_evaluation)
    metric_id = MetricId(specification.primary_metric)

    partition_condition = cell.partition_condition if cell is not None else None
    proximal_mu = cell.proximal_mu if cell is not None else None
    ditto_weight = cell.ditto_weight if cell is not None else None
    threshold_quantile = cell.threshold_quantile if cell is not None else None
    shrinkage_weight = cell.shrinkage_weight if cell is not None else None
    calibration_sample_count = cell.calibration_sample_count if cell is not None else None

    left = tuple(
        evaluation_metric(
            context=context,
            label=eval_a,
            metric_id=metric_id,
            seed=seed,
            cell=cell,
        )
        for seed in context.seeds
    )
    right = tuple(
        evaluation_metric(
            context=context,
            label=eval_b,
            metric_id=metric_id,
            seed=seed,
            cell=cell,
        )
        for seed in context.seeds
    )

    first_policy_id = context.threshold_policy_id(eval_a)
    second_policy_id = context.threshold_policy_id(eval_b)
    cohort = context.config.seed_cohorts.get(context.experiment.seed_cohort_id)

    if context.statistical_analysis is None:
        raise InvalidAnalysisConfigurationError("Statistical analysis service unavailable in execution context")

    record = context.statistical_analysis.analyze_paired_seed_differences(
        left,
        right,
        metric_id,
        first_policy_id,
        second_policy_id,
        specification.statistical_profile,
        cohort.bootstrap_analysis_seed,
    )
    differences = tuple(first - second for first, second in zip(left, right, strict=True))

    result = PairedThresholdAnalysisResult(
        analysis_label=AnalysisLabel(specification.label),
        metric=record.metric_id,
        first_threshold_policy=first_policy_id,
        second_threshold_policy=second_policy_id,
        training_seeds=context.seeds,
        first_seed_values=left,
        second_seed_values=right,
        first_mean=sum(left) / len(left),
        second_mean=sum(right) / len(right),
        mean_difference=record.mean_difference,
        confidence_interval=record.confidence_interval,
        p_value=None if record.hypothesis_test is None else record.hypothesis_test.p_value,
        rank_biserial=record.effect_size,
        resample_count=record.resample_count,
        analysis_seed=record.analysis_seed,
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
    return (result,)


def evaluation_metric(
    *,
    context: AnalysisExecutionContext,
    label: EvaluationLabel,
    metric_id: MetricId,
    seed: Seed,
    cell: PairedAnalysisCell | None = None,
) -> float:
    """Compute the evaluation metric for one seed and evaluation spec."""
    if metric_id.value != MetricIdentifier.CV_FPR:
        raise InvalidAnalysisConfigurationError(
            f"Statistical execution does not support configured metric '{metric_id.value}'"
        )

    eval_spec = context.evaluation(label)
    overrides = eval_spec.overrides or {}
    quantile_override = overrides.get("quantile")
    shrinkage_override = overrides.get("shrinkage_weight")

    has_quantile_override = isinstance(quantile_override, Mapping)
    cell_quantile = cell.threshold_quantile if cell is not None else None
    cell_shrinkage = cell.shrinkage_weight if cell is not None else None
    cell_partition = cell.partition_condition if cell is not None else None
    cell_mu = cell.proximal_mu if cell is not None else None
    cell_ditto = cell.ditto_weight if cell is not None else None
    cell_calib_count = cell.calibration_sample_count if cell is not None else None

    quantile = cell_quantile if has_quantile_override else context.quantile_for_evaluation(label)

    definition = context.config.metric_definitions.cross_client_aggregation.cv_fpr
    if definition.near_zero_mean_threshold_formula != FormulaIdentifier.CV_FPR_NEAR_ZERO_THRESHOLD:
        raise ScientificContractViolationError(
            "CV(FPR) near-zero threshold formula is not the configured roadmap formula"
        )
    if definition.near_zero_mean_threshold_factor is None:
        raise InvalidAnalysisConfigurationError("CV(FPR) near-zero threshold factor is not configured")
    instability_factor = definition.near_zero_mean_threshold_factor

    replicates: tuple[int | None, ...] = (None,)
    if cell_calib_count is not None:
        subset = context.experiment.calibration_subset
        if subset is None:
            raise InvalidAnalysisConfigurationError(
                "Calibration sample count is invalid for an experiment without a subset contract"
            )
        replicates = tuple(range(subset.replicate_count.value))

    values: list[float] = []
    for replicate in replicates:
        eval_ctx = context.evaluation_context(
            label,
            seed,
            partition_condition=cell_partition,
            proximal_mu=cell_mu,
            ditto_weight=cell_ditto,
            threshold_quantile=cell_quantile if has_quantile_override else None,
            shrinkage_weight=cell_shrinkage if isinstance(shrinkage_override, Mapping) else None,
            calibration_sample_count=cell_calib_count,
            calibration_replicate=replicate,
        )

        if not isinstance(quantile, float):
            raise InvalidAnalysisConfigurationError(f"Evaluation '{label.value}' requires a numeric quantile")
        values.append(
            _read_cv_fpr_metric(
                context=context,
                eval_ctx=eval_ctx,
                quantile=quantile,
                instability_factor=instability_factor,
            )
        )
    return sum(values) / len(values)


def _read_cv_fpr_metric(
    *,
    context: AnalysisExecutionContext,
    eval_ctx,
    quantile: float,
    instability_factor: float,
) -> float:
    frame = context.artifacts.client_metrics(eval_ctx)
    # Polars-to-Python bridge: calculate_fpr_dispersion uses statistics & math functions
    fprs = tuple(
        float(value)
        for value in frame.filter(pl.col(MetricColumn.FALSE_POSITIVE_RATE_STATUS.value) == MetricStatus.AVAILABLE)[
            MetricColumn.FALSE_POSITIVE_RATE.value
        ].to_list()
    )
    dispersion = calculate_fpr_dispersion(fprs, cv_instability_threshold=instability_factor * (1.0 - quantile))
    if dispersion.coefficient_of_variation.status is not MetricStatus.AVAILABLE:
        raise StatisticalProcedureError(
            f"Configured CV(FPR) is unavailable for paired statistical analysis: "
            f"{dispersion.coefficient_of_variation.status.value}"
        )
    if dispersion.coefficient_of_variation.value is None:
        raise StatisticalProcedureError("CV(FPR) coefficient of variation is unexpectedly None")
    return dispersion.coefficient_of_variation.value
