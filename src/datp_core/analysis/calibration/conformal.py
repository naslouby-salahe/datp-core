"""Conformal-coverage (B2-conf) analysis."""

from __future__ import annotations

from math import ceil

import polars as pl

from datp_core.analysis.calibration.contracts import (
    ConformalClientCoverageRecord,
    ConformalCoverageAnalysisResult,
    ConformalSeedCoverageResult,
)
from datp_core.analysis.contracts import CountRatioObservation, PairedAnalysisCell
from datp_core.analysis.enums import CoverageDirection, CoverageStatus
from datp_core.analysis.errors import (
    ArtifactSchemaViolationError,
    InvalidAnalysisConfigurationError,
    PopulationAlignmentError,
    ScientificContractViolationError,
)
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.statistics.descriptive import ratio_of_totals
from datp_core.artifacts.schemas.columns import MetricColumn, ScoreColumn, ThresholdColumn
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

    # Convert calibration counts to a Polars frame and join
    cal_counts = pl.from_dict(
        {
            ThresholdColumn.CLIENT_ID.value: [str(c_id) for c_id, _ in calibration_counts],
            "_calibration_count": [cnt for _, cnt in calibration_counts],
        }
    )
    joined = joined.join(cal_counts, on=ThresholdColumn.CLIENT_ID.value, how="left")

    # Validate completeness of per-client diagnostics
    incomplete = joined.filter(
        pl.col("_calibration_count").is_null()
        | pl.col(ThresholdColumn.FINITE_SAMPLE_RANK.value).is_null()
        | pl.col(ThresholdColumn.ATTAINABILITY_STATUS.value).is_null()
    )
    if incomplete.height > 0:
        raise ArtifactSchemaViolationError("Conformal coverage inputs have incomplete per-client diagnostics")

    # Compute expected finite-sample rank
    expected_rank = pl.min_horizontal(
        ((pl.col("_calibration_count") + 1) * (1.0 - coverage_alpha)).ceil().cast(pl.Int64),
        pl.col("_calibration_count"),
    )

    # Compute expected attainability status
    min_calibration = max(minimum_sample_count, ceil(1.0 / coverage_alpha) - 1)
    expected_status = (
        pl.when(pl.col("_calibration_count") >= min_calibration)
        .then(pl.lit(ConformalAttainabilityStatus.ATTAINABLE.value))
        .otherwise(pl.lit(ConformalAttainabilityStatus.UNATTAINABLE.value))
    )

    # Validate finite-sample diagnostics
    diagnostics_off = joined.filter(
        (pl.col(ThresholdColumn.FINITE_SAMPLE_RANK.value).cast(pl.Int64) != expected_rank)
        | (pl.col(ThresholdColumn.ATTAINABILITY_STATUS.value) != expected_status)
    )
    if diagnostics_off.height > 0:
        raise ScientificContractViolationError(f"Conformal finite-sample diagnostics disagree for seed '{seed.value}'")

    # Validate FPR status consistency
    benign_total_expr = pl.col(MetricColumn.TRUE_NEGATIVES.value) + pl.col(MetricColumn.FALSE_POSITIVES.value)
    fpr_off = joined.filter(
        (benign_total_expr > 0)
        != (pl.col(MetricColumn.FALSE_POSITIVE_RATE_STATUS.value) == MetricStatus.AVAILABLE.value)
    )
    if fpr_off.height > 0:
        raise ScientificContractViolationError(f"Conformal coverage metric status disagrees for seed '{seed.value}'")

    # Compute per-client coverage vectorially
    coverage_expr = (
        pl.when(benign_total_expr > 0)
        .then(pl.col(MetricColumn.TRUE_NEGATIVES.value) / benign_total_expr)
        .otherwise(None)
    )

    # Aggregate seed-level totals (clients with available coverage only)
    has_coverage = coverage_expr.is_not_null()
    true_negatives = joined.filter(has_coverage).select(pl.col(MetricColumn.TRUE_NEGATIVES.value).sum()).item()
    benign_total = joined.filter(has_coverage).select(benign_total_expr.sum()).item()

    # Build per-client coverage frame — the only place where iter_rows is used
    per_client = joined.select(
        pl.col(ThresholdColumn.CLIENT_ID.value),
        coverage_expr.alias("coverage"),
        (coverage_expr - target_coverage).abs().alias("absolute_coverage_error"),
        pl.when(has_coverage)
        .then(pl.lit(CoverageStatus.AVAILABLE.value))
        .otherwise(pl.lit(CoverageStatus.UNAVAILABLE_NO_BENIGN_TEST_RECORDS.value))
        .alias("coverage_status"),
        pl.col(ThresholdColumn.FINITE_SAMPLE_RANK.value).cast(pl.Int64).alias("finite_sample_rank"),
        pl.col(ThresholdColumn.ATTAINABILITY_STATUS.value).alias("attainability_status"),
        pl.col("_calibration_count").alias("calibration_count"),
    )
    # Domain object construction requires Python iteration from Polars
    per_client_records = [
        ConformalClientCoverageRecord(
            client_id=ClientId(str(row.client_id)),  # type: ignore[reportAttributeAccessIssue]
            coverage=row.coverage,  # type: ignore[reportAttributeAccessIssue]
            absolute_coverage_error=row.absolute_coverage_error,  # type: ignore[reportAttributeAccessIssue]
            coverage_status=CoverageStatus(row.coverage_status),  # type: ignore[reportAttributeAccessIssue]
            finite_sample_rank=row.finite_sample_rank,  # type: ignore[reportAttributeAccessIssue]
            attainability_status=ConformalAttainabilityStatus(row.attainability_status),  # type: ignore[reportAttributeAccessIssue]
            calibration_count=row.calibration_count,  # type: ignore[reportAttributeAccessIssue]
        )
        for row in per_client.iter_rows(named=True)
    ]
    return ConformalSeedCoverageResult(
        seed=seed,
        per_client_coverage=tuple(per_client_records),
        benign_true_negatives=true_negatives,
        benign_total=benign_total,
    )


def analyze_conformal_coverage(
    specification: ConformalCoverageAnalysisRecord,
    context: AnalysisExecutionContext,
    _cell: PairedAnalysisCell | None = None,
) -> tuple[ConformalCoverageAnalysisResult, ...]:
    """Execute conformal-coverage analysis across experiment seeds."""
    eval_label = EvaluationLabel(specification.source_evaluation)
    policy_id = context.threshold_policy_id(eval_label)
    policy = context.threshold_policies.get(policy_id)
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
            for client_id, rows in calibration_frame.group_by(ScoreColumn.CLIENT_ID.value, maintain_order=True)
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
        item.coverage for res in seed_results for item in res.per_client_coverage if item.coverage is not None
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
