"""Distribution-mechanism analysis: per-client score-CDF comparison across evaluations, plus the
shared per-seed distribution reader that locked-client distribution analysis also builds on."""

from __future__ import annotations

from collections.abc import Mapping

from datp_core.analysis.artifact_access.metric_query import experiment_evaluation
from datp_core.analysis.artifact_access.reader import read_parquet_frame
from datp_core.analysis.distributions.models import (
    DistributionMechanismAnalysisResult,
    DistributionMechanismRawResult,
    DistributionMechanismSeedResult,
    DistributionMechanismTradeoffResult,
    DistributionMechanismTradeoffSeedResult,
)
from datp_core.artifacts.models import ArtifactRepository
from datp_core.contracts.frames import validate_client_metric_frame, validate_test_score_frame, validate_threshold_frame
from datp_core.core.identifiers import RunId
from datp_core.core.values import Seed
from datp_core.evaluation.distributions import (
    ClientScoreDistributionRecord,
    client_score_distributions,
    threshold_tradeoff,
)
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.models import DistributionMechanismAnalysisRecord, ExperimentRecord
from datp_core.experiments.planning import score_context
from datp_core.pipeline.models import StageJobContext


def distribution_seed_result(
    experiment: ExperimentRecord,
    seed: int,
    evaluations: tuple[str, ...],
    run_id: RunId,
    client_id: str | None,
    *,
    repository: ArtifactRepository,
) -> DistributionMechanismSeedResult:
    result: dict[str, Mapping[str, ClientScoreDistributionRecord]] = {}
    for label in evaluations:
        evaluation = experiment_evaluation(experiment, label)
        context = StageJobContext(
            experiment_id=experiment.identifier,
            seed=seed,
            evaluation_label=label,
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
        )
        missing = f"Distribution artifacts are unavailable for seed {seed}, label '{label}'"
        threshold_frame = validate_threshold_frame(
            read_parquet_frame(repository, run_id, IdentityBuilder.threshold_job_id(context), missing_message=missing)
        )
        metric_frame = validate_client_metric_frame(
            read_parquet_frame(repository, run_id, IdentityBuilder.evaluation_job_id(context), missing_message=missing)
        )
        score_frame = validate_test_score_frame(
            read_parquet_frame(
                repository, run_id, IdentityBuilder.test_score_job_id(score_context(context)), missing_message=missing
            )
        )
        result[label] = client_score_distributions(threshold_frame, metric_frame, score_frame, client_id)
    return DistributionMechanismSeedResult(seed=seed, evaluations=result)


def analyze_distribution_mechanism(
    analysis: DistributionMechanismAnalysisRecord,
    *,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> DistributionMechanismAnalysisResult:
    seed_results = tuple(
        distribution_seed_result(
            experiment, seed.value, analysis.source_evaluations, run_id, None, repository=repository
        )
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


__all__ = ["analyze_distribution_mechanism", "distribution_seed_result"]
