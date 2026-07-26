"""Threshold-stability analysis."""

from __future__ import annotations

import polars as pl
from attrs import define

from datp_core.analysis.contracts import QuantileThresholdPolicy
from datp_core.analysis.enums import SweepDimensionKind
from datp_core.analysis.errors import InvalidAnalysisConfigurationError
from datp_core.analysis.runtime.artifacts import AnalysisInputBundle
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.artifacts.schemas.columns import MetricColumn, ThresholdColumn
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.seeding import Seed
from datp_core.evaluation import MetricStatus
from datp_core.experiments import ExperimentRecord, ThresholdStabilityAnalysisRecord
from datp_core.pipeline.stages.context import StageJobContext


@define(frozen=True, slots=True, kw_only=True)
class ThresholdStabilitySeedResult:
    seed: int
    threshold_variance_across_replicates: float | None
    absolute_attainment_error: float | None
    worst_client_fpr: float | None
    clients_unavailable_at_size: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ThresholdStabilityAnalysisResult:
    analysis_label: str
    calibration_sample_count: int
    replicate_aggregation: str
    independent_inferential_unit: str
    seed_results: tuple[ThresholdStabilitySeedResult, ...]


def analyze_threshold_stability(
    analysis: ThresholdStabilityAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    calibration_sample_count: int | None,
) -> ThresholdStabilityAnalysisResult:
    if calibration_sample_count is None:
        raise InvalidAnalysisConfigurationError(
            "Threshold stability analysis requires a calibration sample-count sweep"
        )
    subset = experiment.calibration_subset
    if subset is None or analysis.per_sweep_cell != SweepDimensionKind.CALIBRATION_SAMPLE_COUNT:
        raise InvalidAnalysisConfigurationError(
            f"Threshold stability analysis '{analysis.label}' has an incompatible subset contract"
        )
    evaluation = next(item for item in experiment.evaluations if item.label == analysis.source_evaluation)
    policy = config.threshold_policies.get(evaluation.threshold_policy_id)
    if not isinstance(policy, QuantileThresholdPolicy):
        raise InvalidAnalysisConfigurationError(
            "Threshold stability analysis requires a quantile threshold policy"
        )
    quantile = policy.quantile
    seed_results: list[ThresholdStabilitySeedResult] = []
    for seed in seeds:
        threshold_values: dict[str, list[float]] = {}
        fpr_values: dict[str, list[float]] = {}
        for replicate in range(subset.replicate_count.value):
            context = StageJobContext(
                experiment_id=experiment.identifier,
                seed=seed.value,
                calibration_sample_count=calibration_sample_count,
                calibration_replicate=replicate,
                evaluation_label=analysis.source_evaluation,
            )
            thresholds = artifacts.threshold_frame(inputs.thresholds(context))
            metrics = artifacts.client_metric_frame(inputs.evaluation_metrics(context))
            for client_id, threshold in thresholds.select(
                ThresholdColumn.CLIENT_ID.value, ThresholdColumn.THRESHOLD.value
            ).iter_rows():
                threshold_values.setdefault(str(client_id), []).append(float(threshold))
            for client_id, fpr in (
                metrics.filter(
                    pl.col(MetricColumn.FALSE_POSITIVE_RATE_STATUS.value) == MetricStatus.AVAILABLE.value
                )
                .select(MetricColumn.CLIENT_ID.value, MetricColumn.FALSE_POSITIVE_RATE.value)
                .iter_rows()
            ):
                fpr_values.setdefault(str(client_id), []).append(float(fpr))
        test_context = StageJobContext(experiment_id=experiment.identifier, seed=seed.value)
        test_clients = set(
            artifacts.test_score_frame(inputs.test_scores(test_context))[ThresholdColumn.CLIENT_ID.value]
        )
        variances = [
            sum((value - (sum(values) / len(values))) ** 2 for value in values) / len(values)
            for values in threshold_values.values()
        ]
        mean_fprs = [sum(values) / len(values) for values in fpr_values.values()]
        seed_results.append(
            ThresholdStabilitySeedResult(
                seed=seed.value,
                threshold_variance_across_replicates=sum(variances) / len(variances) if variances else None,
                absolute_attainment_error=(
                    sum(abs(value - (1.0 - quantile)) for value in mean_fprs) / len(mean_fprs)
                    if mean_fprs
                    else None
                ),
                worst_client_fpr=max(mean_fprs) if mean_fprs else None,
                clients_unavailable_at_size=tuple(sorted(test_clients - set(threshold_values))),
            )
        )
    return ThresholdStabilityAnalysisResult(
        analysis_label=analysis.label,
        calibration_sample_count=calibration_sample_count,
        replicate_aggregation=subset.replicate_aggregation_within_seed,
        independent_inferential_unit=subset.independent_inferential_unit,
        seed_results=tuple(seed_results),
    )
