"""Threshold-stability analysis."""

from __future__ import annotations

from typing import cast as _cast

import polars as pl

from datp_core.analysis.contracts import (
    PairedAnalysisCell,
    QuantileThresholdPolicy,
    ThresholdStabilityAnalysisResult,
    ThresholdStabilitySeedResult,
)
from datp_core.analysis.enums import ReplicateAggregation, SweepDimensionKind
from datp_core.analysis.errors import InvalidAnalysisConfigurationError
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.runner import run_analysis
from datp_core.artifacts.schemas.columns import MetricColumn, ScoreColumn, ThresholdColumn
from datp_core.core.identifiers import AnalysisLabel, ClientId, EvaluationLabel
from datp_core.evaluation import MetricStatus
from datp_core.experiments import ThresholdStabilityAnalysisRecord


@run_analysis.register
def analyze_threshold_stability(
    specification: ThresholdStabilityAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[ThresholdStabilityAnalysisResult, ...]:
    """Execute threshold-stability analysis across experiment seeds."""
    calibration_sample_count = cell.calibration_sample_count if cell is not None else None
    if calibration_sample_count is None:
        raise InvalidAnalysisConfigurationError(
            "Threshold stability analysis requires a calibration sample-count sweep cell"
        )
    subset = context.experiment.calibration_subset
    if subset is None or specification.per_sweep_cell != SweepDimensionKind.CALIBRATION_SAMPLE_COUNT:
        raise InvalidAnalysisConfigurationError(
            f"Threshold stability analysis '{specification.label}' has an incompatible subset contract"
        )

    eval_label = EvaluationLabel(specification.source_evaluation)
    policy_id = context.threshold_policy_id(eval_label)
    policy = context.config.threshold_policies.get(policy_id)
    if not hasattr(policy, "quantile"):
        raise InvalidAnalysisConfigurationError(
            f"Threshold stability requires a quantile-based threshold policy, "
            f"got {type(policy).__name__ if policy is not None else 'None'}"
        )
    quantile = float(_cast(QuantileThresholdPolicy, policy).quantile)

    seed_results: list[ThresholdStabilitySeedResult] = []
    for seed in context.seeds:
        replicate_thresholds: list[pl.DataFrame] = []
        replicate_fpr: list[pl.DataFrame] = []

        for replicate in range(subset.replicate_count.value):
            eval_ctx = context.evaluation_context(
                eval_label,
                seed,
                calibration_sample_count=calibration_sample_count,
                calibration_replicate=replicate,
            )
            thresholds = context.artifacts.thresholds(eval_ctx)
            metrics = context.artifacts.client_metrics(eval_ctx)

            replicate_thresholds.append(
                thresholds.select(
                    pl.col(ThresholdColumn.CLIENT_ID.value).cast(pl.String),
                    pl.col(ThresholdColumn.THRESHOLD.value),
                )
            )
            replicate_fpr.append(
                metrics.filter(
                    pl.col(MetricColumn.FALSE_POSITIVE_RATE_STATUS.value) == MetricStatus.AVAILABLE.value
                ).select(
                    pl.col(MetricColumn.CLIENT_ID.value).cast(pl.String),
                    pl.col(MetricColumn.FALSE_POSITIVE_RATE.value),
                )
            )

        all_thresholds = pl.concat(replicate_thresholds)
        all_fpr = pl.concat(replicate_fpr)

        # Per-client threshold variance (population variance, ddof=0)
        client_threshold_var = all_thresholds.group_by(ThresholdColumn.CLIENT_ID.value).agg(
            pl.col(ThresholdColumn.THRESHOLD.value).var(ddof=0).alias("threshold_variance")
        )

        # Per-client mean FPR across replicates
        client_mean_fpr = all_fpr.group_by(MetricColumn.CLIENT_ID.value).agg(
            pl.col(MetricColumn.FALSE_POSITIVE_RATE.value).mean().alias("mean_fpr")
        )

        # Test score clients — use ScoreColumn for score-frame schema ownership
        test_score_ctx = context.score_context(eval_label, seed)
        test_scores = context.artifacts.test_scores(test_score_ctx)

        # Clients present in test scores but absent from thresholds (anti-join)
        unavailable_df = (
            test_scores.select(pl.col(ScoreColumn.CLIENT_ID.value).cast(pl.String))
            .unique()
            .join(
                all_thresholds.select(pl.col(ThresholdColumn.CLIENT_ID.value).cast(pl.String)).unique(),
                on=ThresholdColumn.CLIENT_ID.value,
                how="anti",
            )
        )
        unavailable_clients = tuple(
            sorted(
                (ClientId(str(cid)) for cid in unavailable_df[ScoreColumn.CLIENT_ID.value]),
                key=lambda c: c.value,
            )
        )

        # Seed-level aggregate statistics
        if client_threshold_var.height == 0:
            threshold_variance_across_replicates: float | None = None
        else:
            threshold_variance_across_replicates = _cast(float, client_threshold_var["threshold_variance"].mean())

        if client_mean_fpr.height == 0:
            absolute_attainment_error: float | None = None
            worst_client_fpr: float | None = None
        else:
            target_fpr = 1.0 - quantile
            mean_fpr_values = client_mean_fpr["mean_fpr"]
            absolute_attainment_error = _cast(float, (mean_fpr_values - target_fpr).abs().mean())
            worst_client_fpr = _cast(float, mean_fpr_values.max())

        seed_results.append(
            ThresholdStabilitySeedResult(
                seed=seed,
                threshold_variance_across_replicates=threshold_variance_across_replicates,
                absolute_attainment_error=absolute_attainment_error,
                worst_client_fpr=worst_client_fpr,
                clients_unavailable_at_size=unavailable_clients,
            )
        )

    result = ThresholdStabilityAnalysisResult(
        analysis_label=AnalysisLabel(specification.label),
        calibration_sample_count=calibration_sample_count,
        replicate_aggregation=ReplicateAggregation(subset.replicate_aggregation_within_seed),
        independent_inferential_unit=subset.independent_inferential_unit,
        seed_results=tuple(seed_results),
    )
    return (result,)
