"""Score-distribution analyses: distribution-mechanism, locked-client distribution, and
quantile-estimation -- the three analysis kinds that compare per-client score CDFs and
threshold-estimator quality against an oracle threshold.
"""

from __future__ import annotations

from io import BytesIO

import polars as pl

from datp_core.analysis.models import (
    DistributionMechanismAnalysisResult,
    DistributionMechanismRawResult,
    DistributionMechanismSeedResult,
    DistributionMechanismTradeoffResult,
    DistributionMechanismTradeoffSeedResult,
    LockedClientDistributionAnalysisResult,
    QuantileEstimationAnalysisResult,
    QuantileEstimationClientResult,
    QuantileEstimationEvaluationResult,
    QuantileEstimationSeedResult,
)
from datp_core.artifacts.models import ArtifactRepository
from datp_core.evaluation.distributions import (
    ClientScoreDistributionRecord,
    calibration_variance_terms,
    client_score_distributions,
    threshold_tradeoff,
)
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.models import (
    DistributionMechanismAnalysisRecord,
    ExperimentRecord,
    LockedClientDistributionAnalysisRecord,
    QuantileEstimationAnalysisRecord,
)
from datp_core.experiments.sweeps import score_context
from datp_core.pipeline.frames import validate_calibration_score_frame, validate_client_metric_frame, validate_test_score_frame, validate_threshold_frame
from datp_core.pipeline.identifiers import RunId
from datp_core.pipeline.models import StageJobContext
from datp_core.pipeline.values import Seed


def distribution_seed_result(
    experiment: ExperimentRecord,
    seed: int,
    evaluations: tuple[str, ...],
    run_id: RunId,
    client_id: str | None,
    *,
    repository: ArtifactRepository,
) -> DistributionMechanismSeedResult:
    result: dict[str, ClientScoreDistributionRecord] = {}
    for label in evaluations:
        evaluation = next(item for item in experiment.evaluations if item.label == label)
        context = StageJobContext(
            experiment_id=experiment.identifier,
            seed=seed,
            evaluation_label=label,
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
        )
        threshold = repository.read(f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}")
        metrics = repository.read(f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}")
        scores = repository.read(f"runs/{run_id.value}/{IdentityBuilder.test_score_job_id(score_context(context)).value}")
        if any(not artifact.found or artifact.payload_bytes is None for artifact in (threshold, metrics, scores)):
            raise ValueError(f"Distribution artifacts are unavailable for seed {seed}, label '{label}'")
        assert threshold.payload_bytes is not None
        assert metrics.payload_bytes is not None
        assert scores.payload_bytes is not None
        result[label] = client_score_distributions(
            validate_threshold_frame(pl.read_parquet(BytesIO(threshold.payload_bytes))),
            validate_client_metric_frame(pl.read_parquet(BytesIO(metrics.payload_bytes))),
            validate_test_score_frame(pl.read_parquet(BytesIO(scores.payload_bytes))),
            client_id,
        )
    return DistributionMechanismSeedResult(seed=seed, evaluations=result)


def threshold_and_calibration_frame(
    *,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seed: int,
    label: str,
    run_id: RunId,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    evaluation = next(item for item in experiment.evaluations if item.label == label)
    context = StageJobContext(
        experiment_id=experiment.identifier,
        seed=seed,
        evaluation_label=label,
        population_id=evaluation.population_id,
        recalibration_mode=evaluation.recalibration_mode,
    )
    threshold = repository.read(f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}")
    calibration = repository.read(
        f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(score_context(context)).value}"
    )
    if not threshold.found or threshold.payload_bytes is None or not calibration.found or calibration.payload_bytes is None:
        raise ValueError(f"Quantile-estimation artifacts are unavailable for seed {seed}, label '{label}'")
    return (
        validate_threshold_frame(pl.read_parquet(BytesIO(threshold.payload_bytes))),
        validate_calibration_score_frame(pl.read_parquet(BytesIO(calibration.payload_bytes))),
    )


def analyze_distribution_mechanism(
    analysis: DistributionMechanismAnalysisRecord,
    *,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> DistributionMechanismAnalysisResult:
    seed_results = tuple(
        distribution_seed_result(experiment, seed.value, analysis.source_evaluations, run_id, None, repository=repository)
        for seed in seeds
    )
    if analysis.field_formulas is None:
        return DistributionMechanismRawResult(
            analysis_label=analysis.label, produced_fields=analysis.produced_fields, seed_results=seed_results
        )
    if len(analysis.source_evaluations) < 2:
        raise ValueError(f"Distribution analysis '{analysis.label}' needs two source evaluations")
    baseline, shifted = analysis.source_evaluations[:2]
    return DistributionMechanismTradeoffResult(
        analysis_label=analysis.label,
        field_formulas=analysis.field_formulas,
        produced_fields=analysis.produced_fields,
        seed_results=tuple(
            DistributionMechanismTradeoffSeedResult(
                seed=result.seed,
                per_client_tradeoff=threshold_tradeoff(result.evaluations[baseline], result.evaluations[shifted]),
            )
            for result in seed_results
        ),
    )


def analyze_locked_client_distribution(
    analysis: LockedClientDistributionAnalysisRecord,
    *,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> LockedClientDistributionAnalysisResult:
    seed_results = tuple(
        distribution_seed_result(
            experiment,
            seed.value,
            analysis.source_evaluations,
            run_id,
            analysis.locked_client_identifier,
            repository=repository,
        )
        for seed in seeds
    )
    return LockedClientDistributionAnalysisResult(
        analysis_label=analysis.label,
        locked_client_identifier=analysis.locked_client_identifier,
        produced_fields=analysis.produced_fields,
        seed_results=seed_results,
    )


def analyze_quantile_estimation(
    analysis: QuantileEstimationAnalysisRecord,
    *,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> QuantileEstimationAnalysisResult:
    seed_results: list[QuantileEstimationSeedResult] = []
    for seed in seeds:
        frames = {
            label: threshold_and_calibration_frame(
                repository=repository, experiment=experiment, seed=seed.value, label=label, run_id=run_id
            )
            for label in analysis.source_evaluations
        }
        oracle = frames[analysis.oracle_reference][0]
        oracle_values = {str(client): float(value) for client, value in oracle.select("client_id", "threshold").iter_rows()}
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


__all__ = [
    "analyze_distribution_mechanism",
    "analyze_locked_client_distribution",
    "analyze_quantile_estimation",
    "distribution_seed_result",
    "threshold_and_calibration_frame",
]
