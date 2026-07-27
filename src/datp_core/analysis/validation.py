"""Anchor-equivalence validation."""

from __future__ import annotations

from datp_core.analysis.comparisons.contracts import (
    AnchorEquivalenceAnalysisResult,
    AnchorEquivalenceChecks,
    AnchorHistoricalReference,
    PairedThresholdAnalysisResult,
)
from datp_core.analysis.contracts import PairedAnalysisCell, PrerequisiteAnalysisReference
from datp_core.analysis.enums import AnalysisResultKind, AnchorCheckIdentifier, AnchorComparisonMode
from datp_core.analysis.errors import InvalidAnalysisConfigurationError
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.core.identifiers import AnalysisLabel, MetricId, ThresholdPolicyId
from datp_core.experiments import AnchorEquivalenceAnalysisRecord


def analyze_anchor_equivalence(
    specification: AnchorEquivalenceAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[AnchorEquivalenceAnalysisResult, ...]:
    """Execute anchor-equivalence validation using prerequisite paired results."""
    source_label = AnalysisLabel(specification.source_analysis)
    comparison_mode = AnchorComparisonMode(specification.comparison_mode)

    if comparison_mode != AnchorComparisonMode.STATISTICAL_FALLBACK:
        raise InvalidAnalysisConfigurationError(
            f"Anchor equivalence analysis '{specification.label}' has unsupported comparison mode "
            f"'{comparison_mode.value}'"
        )

    prereq_ref = PrerequisiteAnalysisReference(
        experiment_id=context.experiment.identifier,
        analysis_label=source_label,
        result_kind=AnalysisResultKind.PAIRED_THRESHOLD,
    )
    source = context.artifacts.prerequisite_result(prereq_ref, PairedThresholdAnalysisResult)

    hist_ref = specification.historical_reference
    if not isinstance(hist_ref, AnchorHistoricalReference):
        hist_ref = AnchorHistoricalReference(
            delta=float(hist_ref["delta"]),
            lower_bound=float(hist_ref["lower_bound"]),
            upper_bound=float(hist_ref["upper_bound"]),
            interval_width=float(hist_ref["interval_width"]),
        )

    delta = source.mean_difference
    low, high = source.confidence_interval.lower_bound, source.confidence_interval.upper_bound
    historical_low = hist_ref.lower_bound
    historical_high = hist_ref.upper_bound

    expected_metric = MetricId(specification.expected_metric)
    expected_policy_1 = ThresholdPolicyId(specification.expected_first_threshold_policy)
    expected_policy_2 = ThresholdPolicyId(specification.expected_second_threshold_policy)

    checks = AnchorEquivalenceChecks(
        positive_reproduced_delta=delta > 0.0,
        reproduced_estimate_within_historical_interval=historical_low <= delta <= historical_high,
        overlapping_confidence_intervals=max(low, historical_low) <= min(high, historical_high),
        no_material_movement_toward_zero=delta >= hist_ref.delta,
        reproduced_interval_width_at_most_1_20x_historical_width=(high - low)
        <= specification.interval_width_tolerance_multiplier * hist_ref.interval_width,
        verified_configuration_and_provenance=(
            str(source.metric) == str(expected_metric)
            and str(source.first_threshold_policy) == str(expected_policy_1)
            and str(source.second_threshold_policy) == str(expected_policy_2)
        ),
    )

    checks_by_name = {
        AnchorCheckIdentifier.POSITIVE_REPRODUCED_DELTA: checks.positive_reproduced_delta,
        AnchorCheckIdentifier.REPRODUCED_ESTIMATE_WITHIN_HISTORICAL_INTERVAL: (
            checks.reproduced_estimate_within_historical_interval
        ),
        AnchorCheckIdentifier.OVERLAPPING_CONFIDENCE_INTERVALS: checks.overlapping_confidence_intervals,
        AnchorCheckIdentifier.NO_MATERIAL_MOVEMENT_TOWARD_ZERO: checks.no_material_movement_toward_zero,
        AnchorCheckIdentifier.REPRODUCED_INTERVAL_WIDTH: (
            checks.reproduced_interval_width_at_most_1_20x_historical_width
        ),
        AnchorCheckIdentifier.VERIFIED_CONFIGURATION_AND_PROVENANCE: checks.verified_configuration_and_provenance,
    }

    configured_requirements = {AnchorCheckIdentifier(req) for req in specification.statistical_fallback_requirements}

    failures = tuple(req for req in configured_requirements if not checks_by_name[req])

    return (
        AnchorEquivalenceAnalysisResult(
            analysis_label=AnalysisLabel(specification.label),
            comparison_mode=comparison_mode,
            source_analysis=source_label,
            passed=not failures,
            failure_reasons=failures,
            checks=checks,
            reproduced_delta=delta,
            reproduced_confidence_interval=(low, high),
            historical_reference=hist_ref,
        ),
    )
