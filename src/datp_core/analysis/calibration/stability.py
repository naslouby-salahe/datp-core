"""Threshold-stability analysis."""

from __future__ import annotations

import polars as pl

from datp_core.analysis.contracts import (
    PairedAnalysisCell,
    ThresholdStabilityAnalysisResult,
    ThresholdStabilitySeedResult,
)
from datp_core.analysis.enums import ReplicateAggregation, SweepDimensionKind
from datp_core.analysis.errors import InvalidAnalysisConfigurationError
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.runner import run_analysis
from datp_core.artifacts.schemas.columns import MetricColumn, ThresholdColumn
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
    q_val = getattr(policy, "quantile", None)
    if q_val is None:
        raise InvalidAnalysisConfigurationError(
            "Threshold stability analysis requires a quantile threshold policy"
        )
    quantile = float(q_val)

    seed_results: list[ThresholdStabilitySeedResult] = []
    for seed in context.seeds:
        threshold_values: dict[ClientId, list[float]] = {}
        fpr_values: dict[ClientId, list[float]] = {}

        for replicate in range(subset.replicate_count.value):
            eval_ctx = context.evaluation_context(
                eval_label,
                seed,
                calibration_sample_count=calibration_sample_count,
                calibration_replicate=replicate,
            )
            thresholds = context.artifacts.thresholds(eval_ctx)
            metrics = context.artifacts.client_metrics(eval_ctx)

            for client_id, threshold in thresholds.select(
                ThresholdColumn.CLIENT_ID.value, ThresholdColumn.THRESHOLD.value
            ).iter_rows():
                cid = ClientId(str(client_id))
                threshold_values.setdefault(cid, []).append(float(threshold))

            for client_id, fpr in (
                metrics.filter(
                    pl.col(MetricColumn.FALSE_POSITIVE_RATE_STATUS.value) == MetricStatus.AVAILABLE.value
                )
                .select(MetricColumn.CLIENT_ID.value, MetricColumn.FALSE_POSITIVE_RATE.value)
                .iter_rows()
            ):
                cid = ClientId(str(client_id))
                fpr_values.setdefault(cid, []).append(float(fpr))

        test_score_ctx = context.score_context(eval_label, seed)
        test_scores = context.artifacts.test_scores(test_score_ctx)
        test_clients = {ClientId(str(cid)) for cid in test_scores[ThresholdColumn.CLIENT_ID.value].unique()}

        variances = [
            sum((value - (sum(values) / len(values))) ** 2 for value in values) / len(values)
            for values in threshold_values.values()
        ]
        mean_fprs = [sum(values) / len(values) for values in fpr_values.values()]
        unavailable_clients = tuple(sorted(test_clients - set(threshold_values), key=lambda c: c.value))

        seed_results.append(
            ThresholdStabilitySeedResult(
                seed=seed,
                threshold_variance_across_replicates=sum(variances) / len(variances) if variances else None,
                absolute_attainment_error=(
                    sum(abs(value - (1.0 - quantile)) for value in mean_fprs) / len(mean_fprs)
                    if mean_fprs
                    else None
                ),
                worst_client_fpr=max(mean_fprs) if mean_fprs else None,
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
