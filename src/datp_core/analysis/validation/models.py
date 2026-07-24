"""Result records for anchor-equivalence validation."""

from __future__ import annotations

from collections.abc import Mapping

from attrs import define


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
    historical_reference: Mapping[str, float | str]


__all__ = ["AnchorEquivalenceAnalysisResult", "AnchorEquivalenceChecks"]
