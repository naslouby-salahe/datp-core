"""Quantile-estimator analysis."""

from __future__ import annotations

import polars as pl

from datp_core.analysis.calibration.contracts import (
    QuantileEstimationAnalysisResult,
    QuantileEstimationClientResult,
    QuantileEstimationEvaluationResult,
    QuantileEstimationSeedResult,
)
from datp_core.analysis.contracts import PairedAnalysisCell
from datp_core.analysis.enums import ProducedField
from datp_core.analysis.errors import ScientificContractViolationError
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.artifacts.schemas.columns import ScoreColumn, ThresholdColumn
from datp_core.core.identifiers import AnalysisLabel, ClientId, EvaluationLabel
from datp_core.evaluation.diagnostics import calculate_calibration_variance
from datp_core.experiments import QuantileEstimationAnalysisRecord


def analyze_quantile_estimation(
    specification: QuantileEstimationAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[QuantileEstimationAnalysisResult, ...]:
    """Execute quantile-estimation analysis across experiment seeds."""
    oracle_label = EvaluationLabel(specification.oracle_reference)
    eval_labels = tuple(EvaluationLabel(label) for label in specification.source_evaluations)
    produced_fields = tuple(ProducedField(field) for field in specification.produced_fields)

    seed_results: list[QuantileEstimationSeedResult] = []
    for seed in context.seeds:
        oracle_ctx = context.evaluation_context(oracle_label, seed)
        oracle_thresholds = context.artifacts.thresholds(oracle_ctx)

        # Validate one unique oracle threshold using Polars
        unique_thresholds = oracle_thresholds.select(ThresholdColumn.THRESHOLD.value).unique()
        if unique_thresholds.height != 1:
            raise ScientificContractViolationError("Quantile-estimation oracle must provide one shared threshold")
        oracle_threshold = float(unique_thresholds.item(0, 0))

        evaluation_results: list[QuantileEstimationEvaluationResult] = []
        for label in eval_labels:
            eval_ctx = context.evaluation_context(label, seed)
            score_ctx = context.score_context(label, seed)
            thresholds = context.artifacts.thresholds(eval_ctx)
            calibration = context.artifacts.calibration_scores(score_ctx)

            # Join thresholds with calibration scores by client
            # Compute exceedance: count(score > threshold) / count(score) per client
            exceedance_frame = (
                calibration.join(
                    thresholds.select(
                        ThresholdColumn.CLIENT_ID.value,
                        ThresholdColumn.THRESHOLD.value,
                        ScoreColumn.TARGET_QUANTILE.value,
                    ),
                    on=ScoreColumn.CLIENT_ID.value,
                    how="inner",
                )
                .group_by(ScoreColumn.CLIENT_ID.value, maintain_order=True)
                .agg(
                    [
                        (pl.col(ScoreColumn.SCORE.value) > pl.col(ThresholdColumn.THRESHOLD.value))
                        .sum()
                        .alias("exceed_count"),
                        pl.col(ScoreColumn.SCORE.value).count().alias("total_count"),
                        pl.col(ThresholdColumn.THRESHOLD.value).first().alias("threshold"),
                        pl.col(ScoreColumn.TARGET_QUANTILE.value).first().alias("target_quantile"),
                    ]
                )
                .with_columns(
                    [
                        (pl.col("exceed_count") / pl.col("total_count")).alias("achieved_exceedance"),
                        (pl.col("threshold") - pl.lit(oracle_threshold)).abs().alias("absolute_threshold_error"),
                        (
                            (pl.col("threshold") - pl.lit(oracle_threshold)).abs() / pl.lit(abs(oracle_threshold))
                            if oracle_threshold != 0.0
                            else pl.lit(None)
                        ).alias("relative_threshold_error"),
                    ]
                )
                .with_columns(
                    [
                        (pl.col("achieved_exceedance") - (pl.lit(1.0) - pl.col("target_quantile"))).alias(
                            "signed_attainment_error"
                        ),
                    ]
                )
                .with_columns(
                    [
                        pl.col("signed_attainment_error").abs().alias("absolute_attainment_error"),
                    ]
                )
            )

            # Domain object construction requires Python iteration from Polars
            client_results: list[QuantileEstimationClientResult] = []
            for row in exceedance_frame.select(
                ScoreColumn.CLIENT_ID.value,
                "achieved_exceedance",
                "absolute_threshold_error",
                "relative_threshold_error",
                "signed_attainment_error",
                "absolute_attainment_error",
            ).iter_rows(named=True):
                rel_err = float(row.relative_threshold_error) if row.relative_threshold_error is not None else None  # type: ignore[reportAttributeAccessIssue]
                ach_exc = float(row.achieved_exceedance) if row.achieved_exceedance is not None else None  # type: ignore[reportAttributeAccessIssue]
                sat_err = float(row.signed_attainment_error) if row.signed_attainment_error is not None else None  # type: ignore[reportAttributeAccessIssue]
                abs_err = float(row.absolute_attainment_error) if row.absolute_attainment_error is not None else None  # type: ignore[reportAttributeAccessIssue]
                client_results.append(
                    QuantileEstimationClientResult(
                        client_id=ClientId(str(row.client_id)),  # type: ignore[reportAttributeAccessIssue]
                        absolute_threshold_error=float(row.absolute_threshold_error),  # type: ignore[reportAttributeAccessIssue]
                        relative_threshold_error=rel_err,
                        achieved_exceedance=ach_exc,
                        signed_attainment_error=sat_err,
                        absolute_attainment_error=abs_err,
                    )
                )

            ddof = context.metric_definitions.cross_client_aggregation.standard_deviation_ddof
            variance_terms = calculate_calibration_variance(calibration, ddof=ddof)
            evaluation_results.append(
                QuantileEstimationEvaluationResult(
                    evaluation_label=label,
                    per_client=tuple(client_results),
                    within_term=variance_terms.within_term,
                    between_term=variance_terms.between_term,
                    between_ratio=variance_terms.between_ratio,
                )
            )
        seed_results.append(
            QuantileEstimationSeedResult(
                seed=seed,
                oracle_threshold=oracle_threshold,
                evaluations=tuple(evaluation_results),
            )
        )
    result = QuantileEstimationAnalysisResult(
        analysis_label=AnalysisLabel(specification.label),
        produced_fields=produced_fields,
        seed_results=tuple(seed_results),
    )
    return (result,)
