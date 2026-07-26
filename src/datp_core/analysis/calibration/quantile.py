"""Quantile-estimator analysis."""

from __future__ import annotations

import polars as pl
from attrs import define

from datp_core.analysis.errors import ScientificContractViolationError
from datp_core.analysis.runtime.artifacts import AnalysisInputBundle
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.artifacts.schemas.columns import ScoreColumn, ThresholdColumn
from datp_core.core.seeding import Seed
from datp_core.evaluation.distributions import calibration_variance_terms
from datp_core.experiments import ExperimentRecord, QuantileEstimationAnalysisRecord
from datp_core.experiments.planning import score_context
from datp_core.pipeline.stages.context import StageJobContext


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
    evaluation_label: str
    per_client: tuple[QuantileEstimationClientResult, ...]
    within_term: float
    between_term: float
    between_ratio: float | None


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimationSeedResult:
    seed: int
    oracle_threshold: float
    evaluations: tuple[QuantileEstimationEvaluationResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class QuantileEstimationAnalysisResult:
    analysis_label: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[QuantileEstimationSeedResult, ...]


def analyze_quantile_estimation(
    analysis: QuantileEstimationAnalysisRecord,
    *,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> QuantileEstimationAnalysisResult:
    seed_results: list[QuantileEstimationSeedResult] = []
    for seed in seeds:
        frames = {
            label: artifacts.threshold_and_calibration_frames(
                inputs.thresholds(
                    _evaluation_context(experiment, label, seed.value)
                ),
                inputs.calibration_scores(
                    score_context(_evaluation_context(experiment, label, seed.value))
                ),
            )
            for label in analysis.source_evaluations
        }
        oracle = frames[analysis.oracle_reference][0]
        oracle_values = {
            str(client): float(value)
            for client, value in oracle.select(
                ThresholdColumn.CLIENT_ID.value, ThresholdColumn.THRESHOLD.value
            ).iter_rows()
        }
        if len(set(oracle_values.values())) != 1:
            raise ScientificContractViolationError(
                "Quantile-estimation oracle must provide one shared threshold"
            )
        oracle_threshold = next(iter(oracle_values.values()))
        evaluation_results: list[QuantileEstimationEvaluationResult] = []
        for label, (thresholds, calibration) in frames.items():
            threshold_values = {
                str(client): float(value)
                for client, value in thresholds.select(
                    ThresholdColumn.CLIENT_ID.value, ThresholdColumn.THRESHOLD.value
                ).iter_rows()
            }
            client_results: list[QuantileEstimationClientResult] = []
            for client, threshold in threshold_values.items():
                values = calibration.filter(
                    pl.col(ScoreColumn.CLIENT_ID.value) == client
                )[ScoreColumn.SCORE.value].to_list()
                exceedance = (
                    sum(float(value) > threshold for value in values) / len(values) if values else None
                )
                target = float(
                    thresholds.filter(pl.col(ThresholdColumn.CLIENT_ID.value) == client)[
                        ScoreColumn.TARGET_QUANTILE.value
                    ][0]
                )
                client_results.append(
                    QuantileEstimationClientResult(
                        client_id=client,
                        absolute_threshold_error=abs(threshold - oracle_threshold),
                        relative_threshold_error=(
                            abs(threshold - oracle_threshold) / abs(oracle_threshold)
                            if oracle_threshold
                            else None
                        ),
                        achieved_exceedance=exceedance,
                        signed_attainment_error=(
                            exceedance - (1.0 - target) if exceedance is not None else None
                        ),
                        absolute_attainment_error=(
                            abs(exceedance - (1.0 - target))
                            if exceedance is not None
                            else None
                        ),
                    )
                )
            variance_terms = calibration_variance_terms(calibration)
            evaluation_results.append(
                QuantileEstimationEvaluationResult(
                    evaluation_label=label,
                    per_client=tuple(client_results),
                    within_term=variance_terms.within_term,
                    between_term=variance_terms.between_term,
                    between_ratio=variance_terms.between_ratio,
                )
            )
        seed_results.append(
            QuantileEstimationSeedResult(
                seed=seed.value,
                oracle_threshold=oracle_threshold,
                evaluations=tuple(evaluation_results),
            )
        )
    return QuantileEstimationAnalysisResult(
        analysis_label=analysis.label,
        produced_fields=analysis.produced_fields,
        seed_results=tuple(seed_results),
    )


def _evaluation_context(experiment: ExperimentRecord, label: str, seed: int) -> StageJobContext:
    evaluation = next(item for item in experiment.evaluations if item.label == label)
    return StageJobContext(
        experiment_id=experiment.identifier,
        seed=seed,
        evaluation_label=label,
        population_id=evaluation.population_id,
        recalibration_mode=evaluation.recalibration_mode,
    )
