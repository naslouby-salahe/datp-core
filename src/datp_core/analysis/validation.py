"""Anchor-equivalence validation."""

from __future__ import annotations

from attrs import define

from datp_core.analysis.contracts import PairedThresholdAnalysisResult
from datp_core.analysis.enums import AnchorCheckIdentifier, AnchorComparisonMode
from datp_core.analysis.errors import InvalidAnalysisConfigurationError
from datp_core.experiments import AnchorEquivalenceAnalysisRecord


@define(frozen=True, slots=True, kw_only=True)
class AnchorHistoricalReference:
    """Typed historical anchor values for equivalence checks."""

    delta: float
    lower_bound: float
    upper_bound: float
    interval_width: float


@define(frozen=True, slots=True, kw_only=True)
class AnchorEquivalenceChecks:
    positive_reproduced_delta: bool
    reproduced_estimate_within_historical_interval: bool
    overlapping_confidence_intervals: bool
    no_material_movement_toward_zero: bool
    reproduced_interval_width_at_most_1_20x_historical_width: bool
    verified_configuration_and_provenance: bool


@define(frozen=True, slots=True, kw_only=True)
class AnchorEquivalenceAnalysisResult:
    analysis_label: str
    comparison_mode: str
    source_analysis: str
    passed: bool
    failure_reasons: tuple[str, ...]
    checks: AnchorEquivalenceChecks
    reproduced_delta: float
    reproduced_confidence_interval: tuple[float, float]
    historical_reference: AnchorHistoricalReference


def analyze_anchor_equivalence(
    analysis: AnchorEquivalenceAnalysisRecord, paired_results: tuple[PairedThresholdAnalysisResult, ...]
) -> AnchorEquivalenceAnalysisResult:
    source = next((item for item in paired_results if item.analysis_label == analysis.source_analysis), None)
    if source is None or analysis.comparison_mode != AnchorComparisonMode.STATISTICAL_FALLBACK:
        raise InvalidAnalysisConfigurationError(
            f"Anchor equivalence analysis '{analysis.label}' has no supported paired source"
        )
    historical = analysis.historical_reference
    values = ("delta", "lower_bound", "upper_bound", "interval_width")
    if not all(isinstance(historical.get(name), (int, float)) for name in values):
        raise InvalidAnalysisConfigurationError(
            f"Anchor equivalence analysis '{analysis.label}' has malformed historical values"
        )
    delta = source.mean_difference
    low, high = source.confidence_interval.lower_bound, source.confidence_interval.upper_bound
    historical_low = float(historical["lower_bound"])
    historical_high = float(historical["upper_bound"])
    historical_ref = AnchorHistoricalReference(
        delta=float(historical["delta"]),
        lower_bound=historical_low,
        upper_bound=historical_high,
        interval_width=float(historical["interval_width"]),
    )
    checks = AnchorEquivalenceChecks(
        positive_reproduced_delta=delta > 0.0,
        reproduced_estimate_within_historical_interval=historical_low <= delta <= historical_high,
        overlapping_confidence_intervals=max(low, historical_low) <= min(high, historical_high),
        no_material_movement_toward_zero=delta >= historical_ref.delta,
        reproduced_interval_width_at_most_1_20x_historical_width=(high - low)
        <= analysis.interval_width_tolerance_multiplier * historical_ref.interval_width,
        verified_configuration_and_provenance=(
            source.metric == analysis.expected_metric
            and source.first_threshold_policy == analysis.expected_first_threshold_policy
            and source.second_threshold_policy == analysis.expected_second_threshold_policy
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
    configured_requirements = {
        AnchorCheckIdentifier(req) for req in analysis.statistical_fallback_requirements
    }
    unsupported = sorted(
        req.value for req in configured_requirements if req not in checks_by_name
    )
    if unsupported:
        raise InvalidAnalysisConfigurationError(
            f"Anchor equivalence analysis '{analysis.label}' has unsupported requirements: {unsupported}"
        )
    failures = tuple(
        req.value for req in configured_requirements if not checks_by_name[req]
    )
    return AnchorEquivalenceAnalysisResult(
        analysis_label=analysis.label,
        comparison_mode=analysis.comparison_mode,
        source_analysis=analysis.source_analysis,
        passed=not failures,
        failure_reasons=failures,
        checks=checks,
        reproduced_delta=delta,
        reproduced_confidence_interval=(low, high),
        historical_reference=historical_ref,
    )
