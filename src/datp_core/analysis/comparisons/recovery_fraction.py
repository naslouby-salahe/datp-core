"""Recovery-fraction analysis: how much of a stress condition's threshold-policy gap is recovered
relative to a shared paired-source pair."""

from __future__ import annotations

from datp_core.analysis.comparisons.absorption import materiality_threshold
from datp_core.analysis.comparisons.models import PairedThresholdAnalysisResult, RecoveryFractionAnalysisResult
from datp_core.experiments.models import RecoveryFractionAnalysisRecord


def analyze_recovery_fraction(
    analysis: RecoveryFractionAnalysisRecord, paired_results: tuple[PairedThresholdAnalysisResult, ...]
) -> RecoveryFractionAnalysisResult:
    numerator = next(
        (result for result in paired_results if result.analysis_label == analysis.numerator_analysis), None
    )
    denominator_component = next(
        (result for result in paired_results if result.analysis_label == analysis.denominator_analysis), None
    )
    if numerator is None or denominator_component is None:
        raise ValueError(f"Recovery analysis '{analysis.label}' lacks its paired source analyses")
    numerator_values = numerator.seed_differences
    component_values = denominator_component.seed_differences
    if len(numerator_values) != len(component_values):
        raise ValueError(f"Recovery analysis '{analysis.label}' has malformed paired seed differences")
    if analysis.denominator_composition != "shared_minus_local_gap_of_the_same_seed":
        raise ValueError(f"Recovery analysis '{analysis.label}' has an unsupported denominator composition")
    materiality = materiality_threshold(analysis.denominator_materiality_rule)
    seed_ratios = [
        None
        if abs(numerator_value + component_value) < materiality
        else numerator_value / (numerator_value + component_value)
        for numerator_value, component_value in zip(numerator_values, component_values, strict=True)
    ]
    defined = [value for value in seed_ratios if value is not None]
    return RecoveryFractionAnalysisResult(
        analysis_label=analysis.label,
        formula=analysis.formula,
        undefined_denominator_behavior=analysis.undefined_denominator_behavior,
        per_seed_recovery_fraction=tuple(seed_ratios),
        defined_seed_count=len(defined),
        mean_defined_recovery_fraction=sum(defined) / len(defined) if defined else None,
    )


__all__ = ["analyze_recovery_fraction"]
