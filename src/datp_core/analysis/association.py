"""Metric-association analysis: predictor/outcome correlation between a heterogeneity diagnostic
(pairwise JS divergence) and a paired-threshold outcome (CV(FPR) delta)."""

from __future__ import annotations

from io import BytesIO

import polars as pl

from datp_core.analysis.models import (
    AssociationCorrelationResult,
    AssociationObservationRecord,
    AssociationRegressionResult,
    MetricAssociationAnalysisResult,
    PairedThresholdAnalysisResult,
    StatisticalAnalysisUseCase,
)
from datp_core.artifacts.models import ArtifactRepository
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.evaluation.models import calculate_pairwise_js_divergence
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.models import ExperimentRecord, MetricAssociationAnalysisRecord
from datp_core.pipeline.frames import validate_calibration_score_frame
from datp_core.pipeline.identifiers import ClientId, RunId
from datp_core.pipeline.models import StageJobContext


def analyze_association(
    analysis: MetricAssociationAnalysisRecord,
    paired_results: tuple[PairedThresholdAnalysisResult, ...],
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    statistical_analysis: StatisticalAnalysisUseCase,
    experiment: ExperimentRecord,
    seeds: tuple[int, ...],
    run_id: RunId,
) -> MetricAssociationAnalysisResult:
    if analysis.predictor_metric != "pairwise_js_divergence" or analysis.outcome_metric != "cv_fpr_delta":
        raise ValueError(f"Unsupported association metrics for analysis '{analysis.label}'")
    source = tuple(result for result in paired_results if result.analysis_label == analysis.outcome_source_analysis)
    if not source:
        raise ValueError(f"Association analysis '{analysis.label}' has no paired source analysis")
    observations: list[AssociationObservationRecord] = []
    for result in source:
        condition = result.partition_condition
        if condition is None:
            raise ValueError("Association analysis requires partition-conditioned paired results")
        differences = result.seed_differences
        if len(differences) != len(seeds):
            raise ValueError("Association source has an incomplete paired seed cohort")
        for seed, difference in zip(seeds, differences, strict=True):
            observations.append(
                AssociationObservationRecord(
                    partition_condition=condition,
                    seed=seed,
                    pairwise_js_divergence=calibration_js(
                        config=config, repository=repository, experiment=experiment, seed=seed,
                        partition_condition=condition, run_id=run_id,
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
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seed: int,
    partition_condition: str,
    run_id: RunId,
) -> float:
    context = StageJobContext(experiment_id=experiment.identifier, seed=seed, partition_condition=partition_condition)
    artifact = repository.read(f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(context).value}")
    if not artifact.found or artifact.payload_bytes is None:
        raise ValueError(f"Calibration score artifact is unavailable for seed {seed}, condition '{partition_condition}'")
    frame = validate_calibration_score_frame(pl.read_parquet(BytesIO(artifact.payload_bytes)))
    diagnostics = config.metric_definitions.heterogeneity_diagnostics.pairwise_js_divergence
    return calculate_pairwise_js_divergence(
        tuple(
            (ClientId(client[0]), tuple(float(value) for value in group["score"].to_list()))
            for client, group in frame.group_by("client_id", maintain_order=True)
        ),
        histogram_bins=diagnostics.histogram_bins,
        logarithm_base=diagnostics.logarithm_base,
    )


__all__ = ["analyze_association", "calibration_js"]
