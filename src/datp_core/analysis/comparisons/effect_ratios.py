"""Ratio-based effect analyses: absorption (denominator-materialized ratio of paired differences)
and recovery fraction (gap-recovery relative to a shared paired-source pair).
"""

from __future__ import annotations

from collections.abc import Mapping

from datp_core.analysis.contracts import (
    AbsorptionAnalysisResult,
    PairedAnalysisCell,
    PairedThresholdAnalysisResult,
    PrerequisiteAnalysisReference,
    RecoveryFractionAnalysisResult,
)
from datp_core.analysis.enums import (
    AnalysisResultKind,
    DenominatorComposition,
    UndefinedDenominatorBehavior,
)
from datp_core.analysis.errors import (
    InvalidAnalysisConfigurationError,
    ScientificContractViolationError,
)
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.runner import run_analysis
from datp_core.core.identifiers import AnalysisLabel, ExperimentId
from datp_core.experiments import (
    AbsorptionAnalysisRecord,
    RecoveryFractionAnalysisRecord,
)


def absorption_analysis_result(
    *,
    label: AnalysisLabel,
    formula: str,
    numerator_seed_differences: tuple[float, ...],
    denominator_seed_differences: tuple[float, ...],
    materiality_threshold_value: float,
    undefined_behavior: UndefinedDenominatorBehavior,
) -> AbsorptionAnalysisResult:
    """Calculate ratio of paired differences across seeds with materiality thresholding."""
    if len(numerator_seed_differences) != len(denominator_seed_differences):
        raise ScientificContractViolationError(
            f"Ratio analysis '{label.value}' has malformed paired seed differences"
        )
    ratios = [
        None if abs(denominator_value) < materiality_threshold_value else numerator_value / denominator_value
        for numerator_value, denominator_value in zip(
            numerator_seed_differences, denominator_seed_differences, strict=True
        )
    ]
    defined = [value for value in ratios if value is not None]
    denominator_mean = sum(denominator_seed_differences) / len(denominator_seed_differences)
    return AbsorptionAnalysisResult(
        analysis_label=label,
        formula=formula,
        undefined_denominator_behavior=undefined_behavior,
        per_seed_ratio=tuple(ratios),
        defined_seed_count=len(defined),
        mean_defined_ratio=sum(defined) / len(defined) if defined else None,
        ratio_of_seed_means=(
            (sum(numerator_seed_differences) / len(numerator_seed_differences)) / denominator_mean
            if abs(denominator_mean) >= materiality_threshold_value
            else None
        ),
    )


def _validate_absorption_contract(
    specification: AbsorptionAnalysisRecord, context: AnalysisExecutionContext, reference_exp_id: ExperimentId
) -> None:
    if reference_exp_id != context.experiment.identifier:
        raise InvalidAnalysisConfigurationError(
            f"Absorption analysis '{specification.label}' references non-local experiment '{reference_exp_id.value}'"
        )


@run_analysis.register
def analyze_absorption(
    specification: AbsorptionAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[AbsorptionAnalysisResult, ...]:
    """Execute absorption ratio analysis."""
    stress_label = AnalysisLabel(specification.stress_test_analysis)
    stress_ref = PrerequisiteAnalysisReference(
        experiment_id=context.experiment.identifier,
        analysis_label=stress_label,
        result_kind=AnalysisResultKind.PAIRED_THRESHOLD,
    )
    stress = context.artifacts.prerequisite_result(stress_ref, PairedThresholdAnalysisResult)

    ref_analysis = specification.reference_analysis
    if isinstance(ref_analysis, Mapping):
        reference_exp_id = (
            ExperimentId(str(ref_analysis["experiment_id"]))
            if "experiment_id" in ref_analysis
            else context.experiment.identifier
        )
        reference_label = (
            AnalysisLabel(str(ref_analysis["analysis_label"]))
            if "analysis_label" in ref_analysis
            else AnalysisLabel("")
        )
    elif isinstance(ref_analysis, str):
        reference_exp_id = context.experiment.identifier
        reference_label = AnalysisLabel(ref_analysis)
    else:
        reference_exp_id = ExperimentId(str(getattr(ref_analysis, "experiment_id", context.experiment.identifier)))
        reference_label = AnalysisLabel(str(getattr(ref_analysis, "analysis_label", "")))

    _validate_absorption_contract(specification, context, reference_exp_id)
    ref_paired_ref = PrerequisiteAnalysisReference(
        experiment_id=reference_exp_id,
        analysis_label=reference_label,
        result_kind=AnalysisResultKind.PAIRED_THRESHOLD,
    )
    reference_paired_result = context.artifacts.prerequisite_result(ref_paired_ref, PairedThresholdAnalysisResult)

    materiality_val = float(specification.denominator_materiality_rule)
    undefined_behavior = UndefinedDenominatorBehavior(specification.undefined_denominator_behavior)

    res = absorption_analysis_result(
        label=AnalysisLabel(specification.label),
        formula=specification.formula,
        numerator_seed_differences=stress.seed_differences,
        denominator_seed_differences=reference_paired_result.seed_differences,
        materiality_threshold_value=materiality_val,
        undefined_behavior=undefined_behavior,
    )
    return (res,)


@run_analysis.register
def analyze_recovery_fraction(
    specification: RecoveryFractionAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[RecoveryFractionAnalysisResult, ...]:
    """Execute recovery fraction ratio analysis."""
    num_label = AnalysisLabel(specification.numerator_analysis)
    den_label = AnalysisLabel(specification.denominator_analysis)

    num_ref = PrerequisiteAnalysisReference(
        experiment_id=context.experiment.identifier,
        analysis_label=num_label,
        result_kind=AnalysisResultKind.PAIRED_THRESHOLD,
    )
    den_ref = PrerequisiteAnalysisReference(
        experiment_id=context.experiment.identifier,
        analysis_label=den_label,
        result_kind=AnalysisResultKind.PAIRED_THRESHOLD,
    )
    numerator = context.artifacts.prerequisite_result(num_ref, PairedThresholdAnalysisResult)
    denominator_component = context.artifacts.prerequisite_result(den_ref, PairedThresholdAnalysisResult)

    numerator_values = numerator.seed_differences
    component_values = denominator_component.seed_differences
    if len(numerator_values) != len(component_values):
        raise InvalidAnalysisConfigurationError(
            f"Recovery analysis '{specification.label}' has malformed paired seed differences"
        )

    if specification.denominator_composition != DenominatorComposition.GAP:
        raise InvalidAnalysisConfigurationError(
            f"Recovery analysis '{specification.label}' has an unsupported denominator composition"
        )

    materiality = float(specification.denominator_materiality_rule)
    undefined_behavior = UndefinedDenominatorBehavior(specification.undefined_denominator_behavior)

    seed_ratios = [
        None
        if abs(numerator_value + component_value) < materiality
        else numerator_value / (numerator_value + component_value)
        for numerator_value, component_value in zip(numerator_values, component_values, strict=True)
    ]
    defined = [value for value in seed_ratios if value is not None]

    res = RecoveryFractionAnalysisResult(
        analysis_label=AnalysisLabel(specification.label),
        formula=specification.formula,
        undefined_denominator_behavior=undefined_behavior,
        per_seed_recovery_fraction=tuple(seed_ratios),
        defined_seed_count=len(defined),
        mean_defined_recovery_fraction=sum(defined) / len(defined) if defined else None,
    )
    return (res,)
