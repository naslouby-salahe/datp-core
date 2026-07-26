"""Conformal-coverage (B2-conf) analysis."""

from __future__ import annotations

from math import ceil

import polars as pl

from datp_core.analysis.artifact_access.reader import read_parquet_frame
from datp_core.analysis.calibration.models import (
    ConformalClientCoverageRecord,
    ConformalCoverageAnalysisResult,
    ConformalSeedCoverageResult,
)
from datp_core.analysis.execution.inputs import AnalysisInputBundle
from datp_core.analysis.statistics.descriptive import weighted_mean
from datp_core.artifacts.schemas.metrics import validate_client_metric_frame
from datp_core.artifacts.schemas.scores import validate_calibration_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.seeding import Seed
from datp_core.evaluation import MetricStatus
from datp_core.experiments import ConformalCoverageAnalysisRecord, ExperimentRecord
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.thresholding.policies.conformal import SplitConformalThresholdPolicyRecord
from datp_core.thresholding.policies.enums import ConformalAttainabilityStatus


def conformal_seed_coverage(
    thresholds: pl.DataFrame,
    metrics: pl.DataFrame,
    calibration_counts: dict[str, int],
    target_coverage: float,
    coverage_alpha: float,
    minimum_sample_count: int,
    *,
    seed: int,
) -> ConformalSeedCoverageResult:
    required = ("finite_sample_rank", "attainability_status")
    if any(field not in thresholds.columns for field in required):
        raise ValueError("Conformal threshold artifact lacks finite-sample diagnostics")
    joined = thresholds.join(metrics, on="client_id", how="left")
    if joined.height != thresholds.height or joined["true_negatives"].null_count() > 0:
        raise ValueError("Conformal coverage metrics do not cover the threshold population")
    per_client: dict[str, ConformalClientCoverageRecord] = {}
    coverages: list[float] = []
    true_negatives = 0
    benign_total = 0
    for client, rank, attainability, tn, fp, fpr_status in joined.select(
        "client_id",
        "finite_sample_rank",
        "attainability_status",
        "true_negatives",
        "false_positives",
        "false_positive_rate_status",
    ).iter_rows():
        client_id = str(client)
        count = calibration_counts.get(client_id)
        if count is None or rank is None or attainability is None:
            raise ValueError("Conformal coverage inputs have incomplete per-client diagnostics")
        expected_rank = min(ceil((count + 1) * (1.0 - coverage_alpha)), count)
        expected_status = (
            ConformalAttainabilityStatus.ATTAINABLE
            if count >= max(minimum_sample_count, ceil(1.0 / coverage_alpha) - 1)
            else ConformalAttainabilityStatus.UNATTAINABLE
        )
        if int(rank) != expected_rank or attainability != expected_status.value:
            raise ValueError(
                f"Conformal finite-sample diagnostics disagree for client '{client_id}'")
        client_true_negatives = int(tn)
        client_benign_total = client_true_negatives + int(fp)
        if (client_benign_total > 0) != (fpr_status == MetricStatus.AVAILABLE.value):
            raise ValueError(f"Conformal coverage metric status disagrees for client '{client_id}'")
        coverage = client_true_negatives / client_benign_total if client_benign_total else None
        if coverage is not None:
            coverages.append(coverage)
            true_negatives += client_true_negatives
            benign_total += client_benign_total
        per_client[client_id] = ConformalClientCoverageRecord(
            coverage=coverage,
            absolute_coverage_error=abs(
                coverage - target_coverage) if coverage is not None else None,
            coverage_status="available" if coverage is not None else "unavailable_no_benign_test_records",
            finite_sample_rank=int(rank),
            attainability_status=attainability,
            calibration_count=count,
        )
    return ConformalSeedCoverageResult(
        seed=seed,
        per_client_coverage=per_client,
        client_coverages=tuple(coverages),
        finite_sample_rank={client: record.finite_sample_rank for client,
            record in per_client.items()},
        attainability_status={client: record.attainability_status for client,
            record in per_client.items()},
        benign_true_negatives=true_negatives,
        benign_total=benign_total,
    )


def analyze_conformal_coverage(
    analysis: ConformalCoverageAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    store: ArtifactStore,
    inputs: AnalysisInputBundle,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> ConformalCoverageAnalysisResult:
    evaluation = next(item for item in experiment.evaluations if item.label ==
                      analysis.source_evaluation)
    policy = config.threshold_policies.get(evaluation.threshold_policy_id)
    if not isinstance(policy, SplitConformalThresholdPolicyRecord):
        raise ValueError(
            f"Conformal analysis '{analysis.label}' requires a split-conformal threshold policy")
    if abs(analysis.target_coverage - policy.nominal_coverage) > 1e-12:
        raise ValueError(
            f"Conformal analysis '{analysis.label}' target disagrees with its threshold policy")
    seed_results: list[ConformalSeedCoverageResult] = []
    for seed in seeds:
        context = StageJobContext(
            experiment_id=experiment.identifier,
            seed=seed.value,
            evaluation_label=evaluation.label,
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
        )
        threshold_frame = validate_threshold_frame(
            read_parquet_frame(
                store,
                inputs.thresholds(context),
                missing_message=f"Conformal coverage artifacts are unavailable for seed {seed.value}",
            )
        )
        metric_frame = validate_client_metric_frame(
            read_parquet_frame(
                store,
                inputs.evaluation_metrics(context),
                missing_message=f"Conformal coverage artifacts are unavailable for seed {seed.value}",
            )
        )
        calibration_frame = validate_calibration_score_frame(
            read_parquet_frame(
                store,
                inputs.calibration_scores(
                    StageJobContext(
                        experiment_id=experiment.identifier,
                        seed=seed.value,
                        partition_condition=context.partition_condition,
                        population_id=evaluation.population_id,
                    )
                ),
                missing_message=f"Conformal coverage artifacts are unavailable for seed {seed.value}",
            )
        )
        calibration_counts = {
            str(client_id[0]): len(rows)
            for client_id, rows in calibration_frame.group_by("client_id", maintain_order=True)
        }
        seed_results.append(
            conformal_seed_coverage(
                threshold_frame,
                metric_frame,
                calibration_counts,
                analysis.target_coverage,
                policy.coverage_alpha,
                policy.minimum_sample_count,
                seed=seed.value,
            )
        )
    achieved_marginal = weighted_mean(
        [(result.benign_true_negatives, result.benign_total) for result in seed_results])
    macro_coverages = [value for result in seed_results for value in result.client_coverages]
    achieved_macro = sum(macro_coverages) / len(macro_coverages) if macro_coverages else None
    return ConformalCoverageAnalysisResult(
        analysis_label=analysis.label,
        target_coverage=analysis.target_coverage,
        achieved_marginal_coverage=achieved_marginal,
        achieved_macro_client_coverage=achieved_macro,
        per_client_coverage=tuple(result.per_client_coverage for result in seed_results),
        absolute_coverage_error=(
            abs(achieved_marginal - analysis.target_coverage) if achieved_marginal is not None else None
        ),
        finite_sample_rank=tuple(result.finite_sample_rank for result in seed_results),
        attainability_status=tuple(result.attainability_status for result in seed_results),
        coverage_direction=analysis.coverage_direction,
        seed_results=tuple(seed_results),
    )


__all__ = ["analyze_conformal_coverage", "conformal_seed_coverage"]
