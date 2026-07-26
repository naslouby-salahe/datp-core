"""Distribution-mechanism and locked-client distribution analyses."""

from __future__ import annotations

from collections.abc import Mapping

from attrs import define

from datp_core.analysis.errors import ScientificContractViolationError
from datp_core.analysis.runtime.artifacts import AnalysisInputBundle
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.core.seeding import Seed
from datp_core.evaluation.distributions import (
    ClientScoreDistributionRecord,
    ThresholdTradeoffEntry,
    client_score_distributions,
    threshold_tradeoff,
)
from datp_core.experiments import (
    DistributionMechanismAnalysisRecord,
    ExperimentRecord,
    LockedClientDistributionAnalysisRecord,
)
from datp_core.experiments.planning import score_context
from datp_core.pipeline.stages.context import StageJobContext


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismSeedResult:
    seed: int
    evaluations: Mapping[str, Mapping[str, ClientScoreDistributionRecord]]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismRawResult:
    analysis_label: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[DistributionMechanismSeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismTradeoffSeedResult:
    seed: int
    per_client_tradeoff: Mapping[str, ThresholdTradeoffEntry]


@define(frozen=True, slots=True, kw_only=True)
class DistributionMechanismTradeoffResult:
    analysis_label: str
    field_formulas: Mapping[str, str]
    produced_fields: tuple[str, ...]
    seed_results: tuple[DistributionMechanismTradeoffSeedResult, ...]


DistributionMechanismAnalysisResult = DistributionMechanismRawResult | DistributionMechanismTradeoffResult


@define(frozen=True, slots=True, kw_only=True)
class LockedClientDistributionAnalysisResult:
    analysis_label: str
    locked_client_identifier: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[DistributionMechanismSeedResult, ...]


def _evaluation_spec(experiment: ExperimentRecord, label: str):
    """Return the evaluation spec for *label*."""
    return next(item for item in experiment.evaluations if item.label == label)


def distribution_seed_result(
    experiment: ExperimentRecord,
    seed: int,
    evaluations: tuple[str, ...],
    client_id: str | None,
    *,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
) -> DistributionMechanismSeedResult:
    result: dict[str, Mapping[str, ClientScoreDistributionRecord]] = {}
    for label in evaluations:
        evaluation = _evaluation_spec(experiment, label)
        context = StageJobContext(
            experiment_id=experiment.identifier,
            seed=seed,
            evaluation_label=label,
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
        )
        threshold_frame = artifacts.threshold_frame(inputs.thresholds(context))
        metric_frame = artifacts.client_metric_frame(inputs.evaluation_metrics(context))
        score_frame = artifacts.test_score_frame(inputs.test_scores(score_context(context)))
        result[label] = client_score_distributions(threshold_frame, metric_frame, score_frame, client_id)
    return DistributionMechanismSeedResult(seed=seed, evaluations=result)


def analyze_distribution_mechanism(
    analysis: DistributionMechanismAnalysisRecord,
    *,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> DistributionMechanismAnalysisResult:
    seed_results = tuple(
        distribution_seed_result(
            experiment, seed.value, analysis.source_evaluations, None, artifacts=artifacts, inputs=inputs
        )
        for seed in seeds
    )
    if analysis.field_formulas is None:
        return DistributionMechanismRawResult(
            analysis_label=analysis.label, produced_fields=analysis.produced_fields, seed_results=seed_results
        )
    if len(analysis.source_evaluations) < 2:
        raise ScientificContractViolationError(
            f"Distribution analysis '{analysis.label}' needs two source evaluations"
        )
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
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> LockedClientDistributionAnalysisResult:
    seed_results = tuple(
        distribution_seed_result(
            experiment,
            seed.value,
            analysis.source_evaluations,
            analysis.locked_client_identifier,
            artifacts=artifacts,
            inputs=inputs,
        )
        for seed in seeds
    )
    return LockedClientDistributionAnalysisResult(
        analysis_label=analysis.label,
        locked_client_identifier=analysis.locked_client_identifier,
        produced_fields=analysis.produced_fields,
        seed_results=seed_results,
    )
