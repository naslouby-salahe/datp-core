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
from datp_core.analysis.execution.inputs import AnalysisInputBundle
from datp_core.artifacts.schemas.metrics import validate_client_metric_frame
from datp_core.artifacts.schemas.scores import validate_test_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.core.seeding import Seed
from datp_core.evaluation.distributions import (
    ClientScoreDistributionRecord,
    client_score_distributions,
    threshold_tradeoff,
)
from datp_core.experiments import DistributionMechanismAnalysisRecord, ExperimentRecord
from datp_core.experiments.planning import score_context
from datp_core.pipeline.stages.context import StageJobContext


def distribution_seed_result(
    experiment: ExperimentRecord,
    seed: int,
    evaluations: tuple[str, ...],
    client_id: str | None,
    *,
    store: ArtifactStore,
    inputs: AnalysisInputBundle,
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
            read_parquet_frame(store, inputs.thresholds(context), missing_message=missing)
        )
        metric_frame = validate_client_metric_frame(
            read_parquet_frame(store, inputs.evaluation_metrics(context), missing_message=missing)
        )
        score_frame = validate_test_score_frame(
            read_parquet_frame(
                store,
                inputs.test_scores(score_context(context)),
                missing_message=missing,
            )
        )
        result[label] = client_score_distributions(
            threshold_frame, metric_frame, score_frame, client_id)
    return DistributionMechanismSeedResult(seed=seed, evaluations=result)


def analyze_distribution_mechanism(
    analysis: DistributionMechanismAnalysisRecord,
    *,
    store: ArtifactStore,
    inputs: AnalysisInputBundle,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> DistributionMechanismAnalysisResult:
    seed_results = tuple(
        distribution_seed_result(experiment, seed.value,
                                 analysis.source_evaluations, None, store=store, inputs=inputs)
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
                per_client_tradeoff=threshold_tradeoff(
                    result.evaluations[baseline], result.evaluations[shifted]),
            )
            for result in seed_results
        ),
    )


__all__ = ["analyze_distribution_mechanism", "distribution_seed_result"]
