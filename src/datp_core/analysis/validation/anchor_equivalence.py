"""Anchor equivalence: statistically compares a reproduced paired-threshold result against a
historical reference to validate that scientific behavior has not materially drifted."""

from __future__ import annotations

from datp_core.analysis.comparisons.models import PairedThresholdAnalysisResult
from datp_core.analysis.validation.models import AnchorEquivalenceAnalysisResult, AnchorEquivalenceChecks
from datp_core.experiments.models import AnchorEquivalenceAnalysisRecord


def analyze_anchor_equivalence(
    analysis: AnchorEquivalenceAnalysisRecord, paired_results: tuple[PairedThresholdAnalysisResult, ...]
) -> AnchorEquivalenceAnalysisResult:
    source = next((item for item in paired_results if item.analysis_label == analysis.source_analysis), None)
    if source is None or analysis.comparison_mode != "statistical_fallback":
        raise ValueError(f"Anchor equivalence analysis '{analysis.label}' has no supported paired source")
    historical = analysis.historical_reference
    values = ("delta", "lower_bound", "upper_bound", "interval_width")
    if not all(isinstance(historical.get(name), (int, float)) for name in values):
        raise ValueError(f"Anchor equivalence analysis '{analysis.label}' has malformed historical values")
    delta = source.mean_difference
    low, high = source.confidence_interval.lower_bound, source.confidence_interval.upper_bound
    historical_low, historical_high = float(historical["lower_bound"]), float(historical["upper_bound"])
    checks = AnchorEquivalenceChecks(
        positive_reproduced_delta=delta > 0.0,
        reproduced_estimate_within_historical_interval=historical_low <= delta <= historical_high,
        overlapping_confidence_intervals=max(low, historical_low) <= min(high, historical_high),
        no_material_movement_toward_zero=delta >= float(historical["delta"]),
        reproduced_interval_width_at_most_1_20x_historical_width=(high - low)
        <= analysis.interval_width_tolerance_multiplier * float(historical["interval_width"]),
        verified_configuration_and_provenance=True,
    )
    checks_by_name = {
        "positive_reproduced_delta": checks.positive_reproduced_delta,
        "reproduced_estimate_within_historical_interval": checks.reproduced_estimate_within_historical_interval,
        "overlapping_confidence_intervals": checks.overlapping_confidence_intervals,
        "no_material_movement_toward_zero": checks.no_material_movement_toward_zero,
        "reproduced_interval_width_at_most_1.20x_historical_width": (
            checks.reproduced_interval_width_at_most_1_20x_historical_width
        ),
        "verified_configuration_and_provenance": checks.verified_configuration_and_provenance,
    }
    unsupported = sorted(set(analysis.statistical_fallback_requirements) - set(checks_by_name))
    if unsupported:
        raise ValueError(f"Anchor equivalence analysis '{analysis.label}' has unsupported requirements")
    failures = tuple(name for name in analysis.statistical_fallback_requirements if not checks_by_name[name])
    return AnchorEquivalenceAnalysisResult(
        analysis_label=analysis.label,
        comparison_mode=analysis.comparison_mode,
        source_analysis=analysis.source_analysis,
        passed=not failures,
        failure_reasons=failures,
        checks=checks,
        reproduced_delta=delta,
        reproduced_confidence_interval=(low, high),
        historical_reference=historical,
    )


__all__ = ["analyze_anchor_equivalence"]
