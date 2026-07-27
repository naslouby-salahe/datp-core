"""Metric-association analysis."""

from __future__ import annotations

from datp_core.analysis.comparisons.contracts import (
    AssociationCorrelationResult,
    AssociationObservationRecord,
    AssociationRegressionResult,
    MetricAssociationAnalysisResult,
    PairedThresholdAnalysisResult,
)
from datp_core.analysis.contracts import PairedAnalysisCell, PrerequisiteAnalysisReference
from datp_core.analysis.enums import AnalysisResultKind, MetricIdentifier
from datp_core.analysis.errors import InvalidAnalysisConfigurationError, ScientificContractViolationError
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.artifacts.schemas.columns import ScoreColumn
from datp_core.core.identifiers import AnalysisLabel, ClientId, EvaluationLabel, PartitionConditionId
from datp_core.core.seeding import Seed
from datp_core.evaluation.diagnostics import calculate_pairwise_js_divergence
from datp_core.experiments import MetricAssociationAnalysisRecord


def analyze_association(
    specification: MetricAssociationAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[MetricAssociationAnalysisResult, ...]:
    """Execute metric-association analysis using prerequisite paired results."""
    if (
        specification.predictor_metric != MetricIdentifier.PAIRWISE_JS_DIVERGENCE
        or specification.outcome_metric != MetricIdentifier.CV_FPR_DELTA
    ):
        raise InvalidAnalysisConfigurationError(f"Unsupported association metrics for analysis '{specification.label}'")

    # In single execution architecture, prerequisite results are passed through prerequisite_result or context
    # Note: caller will need to supply paired results or repo lookup.
    # Here we look up prerequisite paired results from repo/context or context artifacts.
    # If no paired result is present, raise error.
    # For standalone dispatch, paired results are loaded from context artifacts or prerequisite frozen results.
    source_label = AnalysisLabel(specification.outcome_source_analysis)

    # Reconstruct observations across seeds
    observations: list[AssociationObservationRecord] = []
    # Fetch prerequisite paired result for outcome source analysis
    prereq_ref = PrerequisiteAnalysisReference(
        experiment_id=context.experiment.identifier,
        analysis_label=source_label,
        result_kind=AnalysisResultKind.PAIRED_THRESHOLD,
    )
    paired_result = context.artifacts.prerequisite_result(prereq_ref, PairedThresholdAnalysisResult)

    condition = paired_result.partition_condition
    if condition is None:
        raise ScientificContractViolationError("Association analysis requires partition-conditioned paired results")

    differences = paired_result.seed_differences
    if len(differences) != len(context.seeds):
        raise ScientificContractViolationError("Association source has an incomplete paired seed cohort")

    cal_eval = (
        EvaluationLabel(specification.calibration_source_evaluation)
        if specification.calibration_source_evaluation
        else EvaluationLabel(context.experiment.evaluations[0].label)
        if context.experiment.evaluations
        else EvaluationLabel("")
    )
    for seed, difference in zip(context.seeds, differences, strict=True):
        observations.append(
            AssociationObservationRecord(
                partition_condition=condition,
                seed=seed,
                pairwise_js_divergence=calibration_js(
                    context=context,
                    seed=seed,
                    partition_condition=condition,
                    evaluation_label=cal_eval,
                ),
                cv_fpr_delta=difference,
            )
        )

    predictor = tuple(item.pairwise_js_divergence for item in observations)
    outcome = tuple(item.cv_fpr_delta for item in observations)

    spearman, regression = context.statistical_analysis.analyze_association(predictor, outcome)

    result = MetricAssociationAnalysisResult(
        analysis_label=AnalysisLabel(specification.label),
        interpretation_constraint=specification.interpretation_constraint,
        spearman=AssociationCorrelationResult(coefficient=spearman.statistic, p_value=spearman.p_value),
        linear_regression=AssociationRegressionResult(
            coefficient=regression.slope,
            intercept=regression.intercept,
            standard_error=regression.standard_error,
            r_squared=regression.r_squared,
            leverage=regression.leverage,
            leave_one_out_slopes=regression.leave_one_out_slopes,
        ),
        observations=tuple(observations),
    )
    return (result,)


def calibration_js(
    *,
    context: AnalysisExecutionContext,
    seed: Seed,
    partition_condition: PartitionConditionId,
    evaluation_label: EvaluationLabel,
) -> float:
    """Compute pairwise Jensen-Shannon divergence for calibration scores of a seed cohort."""
    score_ctx = context.score_context(evaluation_label, seed, partition_condition=partition_condition)
    frame = context.artifacts.calibration_scores(score_ctx)

    diagnostics = context.metric_definitions.heterogeneity_diagnostics.pairwise_js_divergence
    # Polars-to-Python bridge: calculate_pairwise_js_divergence does Python histogram math
    return calculate_pairwise_js_divergence(
        tuple(
            (
                ClientId(str(client[0])),
                tuple(float(value) for value in group[ScoreColumn.SCORE.value].to_list()),
            )
            for client, group in frame.group_by(ScoreColumn.CLIENT_ID.value, maintain_order=True)
        ),
        histogram_bins=diagnostics.histogram_bins,
        logarithm_base=diagnostics.logarithm_base,
    )
