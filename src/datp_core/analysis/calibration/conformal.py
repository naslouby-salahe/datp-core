"""Conformal-coverage (B2-conf) analysis."""

from __future__ import annotations

from math import ceil

import polars as pl
from attrs import define

from datp_core.analysis.enums import CoverageStatus
from datp_core.analysis.errors import (
    ArtifactSchemaViolationError,
    InvalidAnalysisConfigurationError,
    PopulationAlignmentError,
    ScientificContractViolationError,
)
from datp_core.analysis.runtime.artifacts import AnalysisInputBundle
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.analysis.statistics.descriptive import weighted_mean
from datp_core.artifacts.schemas.columns import MetricColumn, ThresholdColumn
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.seeding import Seed
from datp_core.evaluation import MetricStatus
from datp_core.experiments import ConformalCoverageAnalysisRecord, ExperimentRecord
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.thresholding.policies.conformal import SplitConformalThresholdPolicyRecord
from datp_core.thresholding.policies.enums import ConformalAttainabilityStatus

# Floating-point comparison tolerance for coverage target alignment.
# This prevents spurious rejection from FP arithmetic at extreme
# policy/analysis precision.  Not a configurable scientific value.
_COVERAGE_TARGET_TOLERANCE = 1e-12


@define(frozen=True, slots=True, kw_only=True)
class ConformalClientCoverageRecord:
    client_id: str
    coverage: float | None
    absolute_coverage_error: float | None
    coverage_status: CoverageStatus
    finite_sample_rank: int
    attainability_status: ConformalAttainabilityStatus
    calibration_count: int


@define(frozen=True, slots=True, kw_only=True)
class ConformalSeedCoverageResult:
    seed: int
    per_client_coverage: tuple[ConformalClientCoverageRecord, ...]
    client_coverages: tuple[float, ...]
    benign_true_negatives: int
    benign_total: int


@define(frozen=True, slots=True, kw_only=True)
class ConformalCoverageAnalysisResult:
    analysis_label: str
    target_coverage: float
    achieved_marginal_coverage: float | None
    achieved_macro_client_coverage: float | None
    per_client_coverage: tuple[tuple[ConformalClientCoverageRecord, ...], ...]
    absolute_coverage_error: float | None
    coverage_direction: str | None
    seed_results: tuple[ConformalSeedCoverageResult, ...]


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
    required = (ThresholdColumn.FINITE_SAMPLE_RANK.value, ThresholdColumn.ATTAINABILITY_STATUS.value)
    if any(field not in thresholds.columns for field in required):
        raise ArtifactSchemaViolationError("Conformal threshold artifact lacks finite-sample diagnostics")
    joined = thresholds.join(metrics, on=ThresholdColumn.CLIENT_ID.value, how="left")
    if joined.height != thresholds.height or joined[MetricColumn.TRUE_NEGATIVES.value].null_count() > 0:
        raise PopulationAlignmentError("Conformal coverage metrics do not cover the threshold population")
    per_client_records: list[ConformalClientCoverageRecord] = []
    coverages: list[float] = []
    true_negatives = 0
    benign_total = 0
    for client, rank, attainability, tn, fp, fpr_status in joined.select(
        ThresholdColumn.CLIENT_ID.value,
        ThresholdColumn.FINITE_SAMPLE_RANK.value,
        ThresholdColumn.ATTAINABILITY_STATUS.value,
        MetricColumn.TRUE_NEGATIVES.value,
        MetricColumn.FALSE_POSITIVES.value,
        MetricColumn.FALSE_POSITIVE_RATE_STATUS.value,
    ).iter_rows():
        client_id = str(client)
        count = calibration_counts.get(client_id)
        if count is None or rank is None or attainability is None:
            raise ArtifactSchemaViolationError("Conformal coverage inputs have incomplete per-client diagnostics")
        expected_rank = min(ceil((count + 1) * (1.0 - coverage_alpha)), count)
        expected_status = (
            ConformalAttainabilityStatus.ATTAINABLE
            if count >= max(minimum_sample_count, ceil(1.0 / coverage_alpha) - 1)
            else ConformalAttainabilityStatus.UNATTAINABLE
        )
        if int(rank) != expected_rank or attainability != expected_status.value:
            raise ScientificContractViolationError(f"Conformal finite-sample diagnostics disagree for client '{client_id}'")
        client_true_negatives = int(tn)
        client_benign_total = client_true_negatives + int(fp)
        if (client_benign_total > 0) != (fpr_status == MetricStatus.AVAILABLE.value):
            raise ScientificContractViolationError(f"Conformal coverage metric status disagrees for client '{client_id}'")
        coverage = client_true_negatives / client_benign_total if client_benign_total else None
        if coverage is not None:
            coverages.append(coverage)
            true_negatives += client_true_negatives
            benign_total += client_benign_total
        per_client_records.append(ConformalClientCoverageRecord(
            client_id=client_id,
            coverage=coverage,
            absolute_coverage_error=abs(coverage - target_coverage) if coverage is not None else None,
            coverage_status=CoverageStatus.AVAILABLE if coverage is not None else CoverageStatus.UNAVAILABLE_NO_BENIGN_TEST_RECORDS,
            finite_sample_rank=int(rank),
            attainability_status=ConformalAttainabilityStatus(attainability),
            calibration_count=count,
        ))
    return ConformalSeedCoverageResult(
        seed=seed,
        per_client_coverage=tuple(per_client_records),
        client_coverages=tuple(coverages),
        benign_true_negatives=true_negatives,
        benign_total=benign_total,
    )


def analyze_conformal_coverage(
    analysis: ConformalCoverageAnalysisRecord,
    *,
    config: ResolvedProjectConfiguration,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> ConformalCoverageAnalysisResult:
    evaluation = next(item for item in experiment.evaluations if item.label == analysis.source_evaluation)
    policy = config.threshold_policies.get(evaluation.threshold_policy_id)
    if not isinstance(policy, SplitConformalThresholdPolicyRecord):
        raise InvalidAnalysisConfigurationError(f"Conformal analysis '{analysis.label}' requires a split-conformal threshold policy")
    if abs(analysis.target_coverage - policy.nominal_coverage) > _COVERAGE_TARGET_TOLERANCE:
        raise InvalidAnalysisConfigurationError(f"Conformal analysis '{analysis.label}' target disagrees with its threshold policy")
    seed_results: list[ConformalSeedCoverageResult] = []
    for seed in seeds:
        context = StageJobContext(
            experiment_id=experiment.identifier,
            seed=seed.value,
            evaluation_label=evaluation.label,
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
        )
        threshold_frame = artifacts.threshold_frame(inputs.thresholds(context))
        metric_frame = artifacts.client_metric_frame(inputs.evaluation_metrics(context))
        calibration_frame = artifacts.calibration_score_frame(
            inputs.calibration_scores(
                StageJobContext(
                    experiment_id=experiment.identifier,
                    seed=seed.value,
                    partition_condition=context.partition_condition,
                    population_id=evaluation.population_id,
                )
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
    achieved_marginal = weighted_mean([(result.benign_true_negatives, result.benign_total) for result in seed_results])
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
        coverage_direction=analysis.coverage_direction,
        seed_results=tuple(seed_results),
    )
