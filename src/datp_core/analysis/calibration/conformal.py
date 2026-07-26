"""Conformal-coverage (B2-conf) analysis."""

from __future__ import annotations

from math import ceil

import polars as pl

from datp_core.analysis.contracts import (
    ConformalClientCoverageRecord,
    ConformalCoverageAnalysisResult,
    ConformalSeedCoverageResult,
    CountRatioObservation,
    PairedAnalysisCell,
)
from datp_core.analysis.enums import CoverageDirection, CoverageStatus
from datp_core.analysis.errors import (
    ArtifactSchemaViolationError,
    InvalidAnalysisConfigurationError,
    PopulationAlignmentError,
    ScientificContractViolationError,
)
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.runner import run_analysis
from datp_core.analysis.statistics.descriptive import ratio_of_totals
from datp_core.artifacts.schemas.columns import MetricColumn, ThresholdColumn
from datp_core.core.identifiers import AnalysisLabel, ClientId, EvaluationLabel
from datp_core.core.seeding import Seed
from datp_core.evaluation import MetricStatus
from datp_core.experiments import ConformalCoverageAnalysisRecord
from datp_core.thresholding.policies.conformal import SplitConformalThresholdPolicyRecord
from datp_core.thresholding.policies.enums import ConformalAttainabilityStatus

_COVERAGE_TARGET_TOLERANCE = 1e-12


def conformal_seed_coverage(
    thresholds: pl.DataFrame,
    metrics: pl.DataFrame,
    calibration_counts: tuple[tuple[ClientId, int], ...],
    target_coverage: float,
    coverage_alpha: float,
    minimum_sample_count: int,
    *,
    seed: Seed,
) -> ConformalSeedCoverageResult:
    """Compute per-client conformal coverage diagnostics for one seed."""
    required = (ThresholdColumn.FINITE_SAMPLE_RANK.value, ThresholdColumn.ATTAINABILITY_STATUS.value)
    if any(field not in thresholds.columns for field in required):
        raise ArtifactSchemaViolationError("Conformal threshold artifact lacks finite-sample diagnostics")
    joined = thresholds.join(metrics, on=ThresholdColumn.CLIENT_ID.value, how="left")
    if joined.height != thresholds.height or joined[MetricColumn.TRUE_NEGATIVES.value].null_count() > 0:
        raise PopulationAlignmentError("Conformal coverage metrics do not cover the threshold population")

    counts_map = dict(calibration_counts)
    per_client_records: list[ConformalClientCoverageRecord] = []
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
        client_id = ClientId(str(client))
        count = counts_map.get(client_id)
        if count is None or rank is None or attainability is None:
            raise ArtifactSchemaViolationError("Conformal coverage inputs have incomplete per-client diagnostics")
        expected_rank = min(ceil((count + 1) * (1.0 - coverage_alpha)), count)
        expected_status = (
            ConformalAttainabilityStatus.ATTAINABLE
            if count >= max(minimum_sample_count, ceil(1.0 / coverage_alpha) - 1)
            else ConformalAttainabilityStatus.UNATTAINABLE
        )
        if int(rank) != expected_rank or attainability != expected_status.value:
            raise ScientificContractViolationError(
                f"Conformal finite-sample diagnostics disagree for client '{client_id.value}'"
            )
        client_true_negatives = int(tn)
        client_benign_total = client_true_negatives + int(fp)
        if (client_benign_total > 0) != (fpr_status == MetricStatus.AVAILABLE.value):
            raise ScientificContractViolationError(
                f"Conformal coverage metric status disagrees for client '{client_id.value}'"
            )
        coverage = client_true_negatives / client_benign_total if client_benign_total else None
        if coverage is not None:
            true_negatives += client_true_negatives
            benign_total += client_benign_total
        per_client_records.append(
            ConformalClientCoverageRecord(
                client_id=client_id,
                coverage=coverage,
                absolute_coverage_error=abs(coverage - target_coverage) if coverage is not None else None,
                coverage_status=(
                    CoverageStatus.AVAILABLE
                    if coverage is not None
                    else CoverageStatus.UNAVAILABLE_NO_BENIGN_TEST_RECORDS
                ),
                finite_sample_rank=int(rank),
                attainability_status=ConformalAttainabilityStatus(attainability),
                calibration_count=count,
            )
        )
    return ConformalSeedCoverageResult(
        seed=seed,
        per_client_coverage=tuple(per_client_records),
        benign_true_negatives=true_negatives,
        benign_total=benign_total,
    )


@run_analysis.register
def analyze_conformal_coverage(
    specification: ConformalCoverageAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[ConformalCoverageAnalysisResult, ...]:
    """Execute conformal-coverage analysis across experiment seeds."""
    eval_label = EvaluationLabel(specification.source_evaluation)
    policy_id = context.threshold_policy_id(eval_label)
    policy = context.config.threshold_policies.get(policy_id)
    if not isinstance(policy, SplitConformalThresholdPolicyRecord):
        raise InvalidAnalysisConfigurationError(
            f"Conformal analysis '{specification.label}' requires a split-conformal threshold policy"
        )
    if abs(specification.target_coverage - policy.nominal_coverage) > _COVERAGE_TARGET_TOLERANCE:
        raise InvalidAnalysisConfigurationError(
            f"Conformal analysis '{specification.label}' target disagrees with its threshold policy"
        )

    seed_results: list[ConformalSeedCoverageResult] = []
    for seed in context.seeds:
        eval_ctx = context.evaluation_context(eval_label, seed)
        score_ctx = context.score_context(eval_label, seed)
        threshold_frame = context.artifacts.thresholds(eval_ctx)
        metric_frame = context.artifacts.client_metrics(eval_ctx)
        calibration_frame = context.artifacts.calibration_scores(score_ctx)

        calibration_counts = tuple(
            (ClientId(str(client_id[0])), len(rows))
            for client_id, rows in calibration_frame.group_by(MetricColumn.CLIENT_ID.value, maintain_order=True)
        )
        seed_results.append(
            conformal_seed_coverage(
                threshold_frame,
                metric_frame,
                calibration_counts,
                specification.target_coverage,
                policy.coverage_alpha,
                policy.minimum_sample_count,
                seed=seed,
            )
        )

    achieved_marginal = ratio_of_totals(
        [
            CountRatioObservation(
                numerator=float(res.benign_true_negatives),
                denominator=float(res.benign_total),
            )
            for res in seed_results
        ]
    )
    macro_coverages = [
        item.coverage
        for res in seed_results
        for item in res.per_client_coverage
        if item.coverage is not None
    ]
    achieved_macro = sum(macro_coverages) / len(macro_coverages) if macro_coverages else None
    direction = CoverageDirection(specification.coverage_direction) if specification.coverage_direction else None

    result = ConformalCoverageAnalysisResult(
        analysis_label=AnalysisLabel(specification.label),
        target_coverage=specification.target_coverage,
        achieved_marginal_coverage=achieved_marginal,
        achieved_macro_client_coverage=achieved_macro,
        absolute_coverage_error=(
            abs(achieved_marginal - specification.target_coverage) if achieved_marginal is not None else None
        ),
        coverage_direction=direction,
        seed_results=tuple(seed_results),
    )
    return (result,)
