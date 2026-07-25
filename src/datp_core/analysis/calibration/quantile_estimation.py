"""Quantile-estimator analysis: threshold-estimator error against an oracle threshold, and the
calibration-count variance decomposition each evaluation's estimator achieves."""

from __future__ import annotations

import polars as pl

from datp_core.analysis.artifact_access.bundles import threshold_and_calibration_frame
from datp_core.analysis.calibration.models import (
    QuantileEstimationAnalysisResult,
    QuantileEstimationClientResult,
    QuantileEstimationEvaluationResult,
    QuantileEstimationSeedResult,
)
from datp_core.analysis.execution.inputs import AnalysisInputBundle
from datp_core.artifacts.store import ArtifactStore
from datp_core.core.seeding import Seed
from datp_core.evaluation.distributions import calibration_variance_terms
from datp_core.experiments import ExperimentRecord, QuantileEstimationAnalysisRecord
from datp_core.experiments.planning import score_context
from datp_core.pipeline.stages.context import StageJobContext


def analyze_quantile_estimation(
    analysis: QuantileEstimationAnalysisRecord,
    *,
    store: ArtifactStore,
    inputs: AnalysisInputBundle,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> QuantileEstimationAnalysisResult:
    seed_results: list[QuantileEstimationSeedResult] = []
    for seed in seeds:
        frames = {
            label: threshold_and_calibration_frame(
                store=store,
                threshold_path=inputs.thresholds(
                    _evaluation_context(experiment, label, seed.value)
                ),
                calibration_score_path=inputs.calibration_scores(
                    score_context(_evaluation_context(experiment, label, seed.value))
                ),
                missing_message=f"Quantile-estimation artifacts are unavailable for seed {seed.value}, label '{label}'",
            )
            for label in analysis.source_evaluations
        }
        oracle = frames[analysis.oracle_reference][0]
        oracle_values = {
            str(client): float(value) for client, value in oracle.select("client_id", "threshold").iter_rows()
        }
        if len(set(oracle_values.values())) != 1:
            raise ValueError("Quantile-estimation oracle must provide one shared threshold")
        oracle_threshold = next(iter(oracle_values.values()))
        policies: dict[str, QuantileEstimationEvaluationResult] = {}
        for label, (thresholds, calibration) in frames.items():
            threshold_values = {
                str(client): float(value) for client, value in thresholds.select("client_id", "threshold").iter_rows()
            }
            client_results: list[QuantileEstimationClientResult] = []
            for client, threshold in threshold_values.items():
                values = calibration.filter(pl.col("client_id") == client)["score"].to_list()
                exceedance = sum(float(value) > threshold for value in values) / len(values) if values else None
                target = float(thresholds.filter(pl.col("client_id") == client)["target_quantile"][0])
                client_results.append(
                    QuantileEstimationClientResult(
                        client_id=client,
                        absolute_threshold_error=abs(threshold - oracle_threshold),
                        relative_threshold_error=(
                            abs(threshold - oracle_threshold) / abs(oracle_threshold) if oracle_threshold else None
                        ),
                        achieved_exceedance=exceedance,
                        signed_attainment_error=exceedance - (1.0 - target) if exceedance is not None else None,
                        absolute_attainment_error=abs(exceedance - (1.0 - target)) if exceedance is not None else None,
                    )
                )
            variance_terms = calibration_variance_terms(calibration)
            policies[label] = QuantileEstimationEvaluationResult(
                per_client=tuple(client_results),
                within_term=variance_terms.within_term,
                between_term=variance_terms.between_term,
                between_ratio=variance_terms.between_ratio,
            )
        seed_results.append(
            QuantileEstimationSeedResult(seed=seed.value, oracle_threshold=oracle_threshold, evaluations=policies)
        )
    return QuantileEstimationAnalysisResult(
        analysis_label=analysis.label, produced_fields=analysis.produced_fields, seed_results=tuple(seed_results)
    )


__all__ = ["analyze_quantile_estimation"]


def _evaluation_context(experiment: ExperimentRecord, label: str, seed: int) -> StageJobContext:
    evaluation = next(item for item in experiment.evaluations if item.label == label)
    return StageJobContext(
        experiment_id=experiment.identifier,
        seed=seed,
        evaluation_label=label,
        population_id=evaluation.population_id,
        recalibration_mode=evaluation.recalibration_mode,
    )
