"""Threshold-stability analysis: sensitivity of constructed thresholds and achieved FPR to
calibration-sample-count shrinkage across replicates."""

from __future__ import annotations

import polars as pl

from datp_core.analysis.artifact_access.reader import read_parquet_frame
from datp_core.analysis.calibration.models import ThresholdStabilityAnalysisResult, ThresholdStabilitySeedResult
from datp_core.artifacts.models import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.contracts.frames import validate_client_metric_frame, validate_test_score_frame, validate_threshold_frame
from datp_core.core.identifiers import RunId
from datp_core.core.values import Seed
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.models import ExperimentRecord, ThresholdStabilityAnalysisRecord
from datp_core.pipeline.models import StageJobContext


def analyze_threshold_stability(
    analysis: ThresholdStabilityAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
    calibration_sample_count: int | None,
) -> ThresholdStabilityAnalysisResult:
    if calibration_sample_count is None:
        raise ValueError("Threshold stability analysis requires a calibration sample-count sweep")
    subset = experiment.calibration_subset
    if subset is None or analysis.per_sweep_cell != "calibration_sample_count":
        raise ValueError(f"Threshold stability analysis '{analysis.label}' has an incompatible subset contract")
    evaluation = next(item for item in experiment.evaluations if item.label == analysis.source_evaluation)
    policy = config.threshold_policies.get(evaluation.threshold_policy_id)
    quantile = getattr(policy, "quantile", None)
    if not isinstance(quantile, float):
        raise ValueError("Threshold stability analysis requires a quantile threshold policy")
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
            missing = f"Threshold stability artifacts are unavailable for seed {seed.value}"
            thresholds = validate_threshold_frame(
                read_parquet_frame(
                    repository, run_id, IdentityBuilder.threshold_job_id(context), missing_message=missing
                )
            )
            metrics = validate_client_metric_frame(
                read_parquet_frame(
                    repository, run_id, IdentityBuilder.evaluation_job_id(context), missing_message=missing
                )
            )
            for client_id, threshold in thresholds.select("client_id", "threshold").iter_rows():
                threshold_values.setdefault(str(client_id), []).append(float(threshold))
            for client_id, fpr in (
                metrics.filter(pl.col("false_positive_rate_status") == "available")
                .select("client_id", "false_positive_rate")
                .iter_rows()
            ):
                fpr_values.setdefault(str(client_id), []).append(float(fpr))
        test_context = StageJobContext(experiment_id=experiment.identifier, seed=seed.value)
        test_clients = set(
            validate_test_score_frame(
                read_parquet_frame(
                    repository,
                    run_id,
                    IdentityBuilder.test_score_job_id(test_context),
                    missing_message=f"Test scores are unavailable for threshold stability seed {seed.value}",
                )
            )["client_id"]
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
                    sum(abs(value - (1.0 - quantile)) for value in mean_fprs) / len(mean_fprs) if mean_fprs else None
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


__all__ = ["analyze_threshold_stability"]
