"""Temporal-recovery analysis."""

from __future__ import annotations

from datp_core.analysis.comparisons.paired import evaluation_metric
from datp_core.analysis.contracts import PairedAnalysisCell, TemporalRecoveryAnalysisResult
from datp_core.analysis.enums import (
    ChronologyPolicy,
    MetricIdentifier,
    NegativeRecoveryBehavior,
    TemporalOutcomeBand,
)
from datp_core.analysis.errors import InvalidAnalysisConfigurationError, ScientificContractViolationError
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.runner import run_analysis
from datp_core.core.identifiers import AnalysisLabel, EvaluationLabel, MetricId
from datp_core.experiments import TemporalRecoveryAnalysisRecord


@run_analysis.register
def analyze_temporal_recovery(
    specification: TemporalRecoveryAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[TemporalRecoveryAnalysisResult, ...]:
    """Execute temporal-recovery analysis across seeds."""
    if specification.primary_metric != MetricIdentifier.CV_FPR:
        raise InvalidAnalysisConfigurationError(
            f"Temporal analysis '{specification.label}' has an unsupported primary metric"
        )

    metric_id = MetricId(specification.primary_metric)
    static_eval = EvaluationLabel(specification.static_reference_evaluation)
    frozen_eval = EvaluationLabel(specification.frozen_evaluation)
    recal_eval = EvaluationLabel(specification.recalibrated_evaluation)

    static = tuple(
        evaluation_metric(context=context, label=static_eval, metric_id=metric_id, seed=seed)
        for seed in context.seeds
    )
    frozen = tuple(
        evaluation_metric(context=context, label=frozen_eval, metric_id=metric_id, seed=seed)
        for seed in context.seeds
    )
    recalibrated = tuple(
        evaluation_metric(context=context, label=recal_eval, metric_id=metric_id, seed=seed)
        for seed in context.seeds
    )

    neg_policy = NegativeRecoveryBehavior(specification.negative_recovery_policy)
    chron_policy = ChronologyPolicy(specification.chronology_unverifiable_policy)

    if chron_policy == ChronologyPolicy.STRICT_VERIFICATION:
        if not getattr(context.experiment, "has_verifiable_chronology", True):
            raise ScientificContractViolationError(
                f"Temporal analysis '{specification.label}' requires verifiable chronology"
            )

    drift = tuple(f_val - s_val for f_val, s_val in zip(frozen, static, strict=True))
    raw_recovered = [f_val - r_val for f_val, r_val in zip(frozen, recalibrated, strict=True)]

    recovered = tuple(
        max(0.0, r) if neg_policy == NegativeRecoveryBehavior.CLAMP_TO_ZERO else r
        for r in raw_recovered
    )

    frozen_policy_id = context.threshold_policy_id(frozen_eval)
    static_policy_id = context.threshold_policy_id(static_eval)
    cohort = context.config.seed_cohorts.get(context.experiment.seed_cohort_id)

    record = context.statistical_analysis.analyze_paired_seed_differences(
        frozen,
        static,
        metric_id,
        frozen_policy_id,
        static_policy_id,
        specification.statistical_profile,
        cohort.bootstrap_analysis_seed,
    )

    meaningful = record.confidence_interval.lower_bound > 0.0
    raw_ratios = [
        rec_val / drift_val if meaningful and drift_val > 0.0 else None
        for rec_val, drift_val in zip(recovered, drift, strict=True)
    ]
    if neg_policy == NegativeRecoveryBehavior.CLAMP_TO_ZERO:
        ratios = tuple(max(0.0, r) if r is not None else None for r in raw_ratios)
    else:
        ratios = tuple(raw_ratios)

    defined = tuple(val for val in ratios if val is not None)

    band = TemporalOutcomeBand.NO_MEANINGFUL_DEGRADATION
    if meaningful:
        mean_ratio = sum(defined) / len(defined) if defined else None
        threshold = specification.meaningful_recovery_threshold
        band = (
            TemporalOutcomeBand.MEANINGFUL_RECOVERY
            if mean_ratio is not None and mean_ratio >= threshold
            else TemporalOutcomeBand.INSUFFICIENT_RECOVERY
        )

    res = TemporalRecoveryAnalysisResult(
        analysis_label=AnalysisLabel(specification.label),
        metric=metric_id,
        static_reference_cv=static,
        frozen_future_cv=frozen,
        recalibrated_future_cv=recalibrated,
        drift_excess=drift,
        recovered_amount=recovered,
        recovery_ratio=ratios,
        meaningful_degradation=meaningful,
        drift_confidence_interval=(record.confidence_interval.lower_bound, record.confidence_interval.upper_bound),
        outcome_band=band,
        defined_recovery_ratio_seed_count=len(defined),
        mean_defined_recovery_ratio=sum(defined) / len(defined) if defined else None,
        negative_recovery_policy=NegativeRecoveryBehavior(specification.negative_recovery_policy),
        chronology_unverifiable_policy=ChronologyPolicy(specification.chronology_unverifiable_policy),
    )
    return (res,)
