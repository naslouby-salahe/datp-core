"""Metric-association analysis."""

from __future__ import annotations

from attrs import define

from datp_core.analysis.contracts import PairedThresholdAnalysisResult
from datp_core.analysis.enums import MetricIdentifier
from datp_core.analysis.errors import InvalidAnalysisConfigurationError, ScientificContractViolationError
from datp_core.analysis.runtime.artifacts import AnalysisInputBundle
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.artifacts.schemas.columns import ScoreColumn
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ClientId
from datp_core.evaluation import calculate_pairwise_js_divergence
from datp_core.experiments import ExperimentRecord, MetricAssociationAnalysisRecord
from datp_core.pipeline.stages.context import StageJobContext


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


def analyze_association(
    analysis: MetricAssociationAnalysisRecord,
    paired_results: tuple[PairedThresholdAnalysisResult, ...],
    *,
    config: ResolvedProjectConfiguration,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    statistical_analysis: StatisticalAnalysisUseCase,
    experiment: ExperimentRecord,
    seeds: tuple[int, ...],
) -> MetricAssociationAnalysisResult:
    if (
        analysis.predictor_metric != MetricIdentifier.PAIRWISE_JS_DIVERGENCE
        or analysis.outcome_metric != MetricIdentifier.CV_FPR_DELTA
    ):
        raise InvalidAnalysisConfigurationError(
            f"Unsupported association metrics for analysis '{analysis.label}'"
        )
    source = tuple(
        result for result in paired_results
        if result.analysis_label == analysis.outcome_source_analysis
    )
    if not source:
        raise InvalidAnalysisConfigurationError(
            f"Association analysis '{analysis.label}' has no paired source analysis"
        )
    observations: list[AssociationObservationRecord] = []
    for result in source:
        condition = result.partition_condition
        if condition is None:
            raise ScientificContractViolationError(
                "Association analysis requires partition-conditioned paired results"
            )
        differences = result.seed_differences
        if len(differences) != len(seeds):
            raise ScientificContractViolationError(
                "Association source has an incomplete paired seed cohort"
            )
        for seed, difference in zip(seeds, differences, strict=True):
            observations.append(
                AssociationObservationRecord(
                    partition_condition=condition,
                    seed=seed,
                    pairwise_js_divergence=calibration_js(
                        config=config,
                        artifacts=artifacts,
                        inputs=inputs,
                        experiment=experiment,
                        seed=seed,
                        partition_condition=condition,
                    ),
                    cv_fpr_delta=difference,
                )
            )
    predictor = tuple(item.pairwise_js_divergence for item in observations)
    outcome = tuple(item.cv_fpr_delta for item in observations)
    spearman, regression = statistical_analysis.analyze_association(predictor, outcome)
    return MetricAssociationAnalysisResult(
        analysis_label=analysis.label,
        interpretation_constraint=analysis.interpretation_constraint,
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


def calibration_js(
    *,
    config: ResolvedProjectConfiguration,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    experiment: ExperimentRecord,
    seed: int,
    partition_condition: str,
) -> float:
    context = StageJobContext(experiment_id=experiment.identifier, seed=seed, partition_condition=partition_condition)
    frame = artifacts.calibration_score_frame(inputs.calibration_scores(context))
    diagnostics = config.metric_definitions.heterogeneity_diagnostics.pairwise_js_divergence
    return calculate_pairwise_js_divergence(
        tuple(
            (
                ClientId(client[0]),
                tuple(float(value) for value in group[ScoreColumn.SCORE.value].to_list()),
            )
            for client, group in frame.group_by(ScoreColumn.CLIENT_ID.value, maintain_order=True)
        ),
        histogram_bins=diagnostics.histogram_bins,
        logarithm_base=diagnostics.logarithm_base,
    )


__all__ = ["analyze_association", "calibration_js"]
