"""Seed-indexed ratio calculations: recovery-fraction and absorption analyses, plus the shared
ratio-of-paired-differences and denominator-materiality machinery they both build on.
"""

from __future__ import annotations

import json
import re

import numpy as np

from datp_core.analysis.results import (
    AbsorptionAnalysisResult,
    PairedThresholdAnalysisResult,
    RecoveryFractionAnalysisResult,
    SeedRatioResult,
)
from datp_core.artifacts.models import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.identity import IdentityBuilder, execution_run_id
from datp_core.experiments.models import AbsorptionAnalysisRecord, ExperimentRecord, RecoveryFractionAnalysisRecord
from datp_core.pipeline.models import StageJobContext


def mean_group_std(groups: list[list[tuple[float, float]]], index: int) -> float | None:
    return float(np.mean([np.std([item[index] for item in group]) for group in groups])) if groups else None


def group_mean_std(groups: list[list[tuple[float, float]]], index: int) -> float | None:
    return float(np.std([np.mean([item[index] for item in group]) for group in groups])) if groups else None


_MATERIALITY_RULE_PATTERN = re.compile(r"^absolute_denominator_at_least_(?P<value>\d+(?:\.\d+)?(?:e[+-]?\d+)?)$")


def materiality_threshold(rule: float | str) -> float:
    """Mechanically extract the numeric denominator-materiality threshold from its authored rule
    name, rather than duplicating the value as a separately hardcoded literal: the rule's name IS
    its value, so a changed threshold in configuration is picked up without a code change."""
    if isinstance(rule, (int, float)):
        return float(rule)
    match = _MATERIALITY_RULE_PATTERN.match(rule)
    if match is None:
        raise ValueError(f"Unsupported denominator materiality rule: {rule!r}")
    return float(match.group("value"))


def weighted_mean(values: list[tuple[int, int]]) -> float | None:
    denominator = sum(weight for _, weight in values)
    return sum(value for value, _ in values) / denominator if denominator else None


def seed_ratio_result(
    *,
    label: str,
    formula: str,
    numerator_seed_differences: tuple[float, ...],
    denominator_seed_differences: tuple[float, ...],
    materiality_rule: float | str,
    undefined_behavior: str,
) -> SeedRatioResult:
    if len(numerator_seed_differences) != len(denominator_seed_differences):
        raise ValueError(f"Ratio analysis '{label}' has malformed paired seed differences")
    materiality = materiality_threshold(materiality_rule)
    ratios = [
        None if abs(denominator_value) < materiality else numerator_value / denominator_value
        for numerator_value, denominator_value in zip(
            numerator_seed_differences, denominator_seed_differences, strict=True
        )
    ]
    defined = [value for value in ratios if value is not None]
    denominator_mean = sum(denominator_seed_differences) / len(denominator_seed_differences)
    return SeedRatioResult(
        analysis_label=label,
        formula=formula,
        undefined_denominator_behavior=undefined_behavior,
        per_seed_ratio=tuple(ratios),
        defined_seed_count=len(defined),
        mean_defined_ratio=sum(defined) / len(defined) if defined else None,
        ratio_of_seed_means=(
            (sum(numerator_seed_differences) / len(numerator_seed_differences)) / denominator_mean
            if abs(denominator_mean) >= materiality
            else None
        ),
    )


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


def analyze_absorption(
    analysis: AbsorptionAnalysisRecord,
    experiment: ExperimentRecord,
    paired_results: tuple[PairedThresholdAnalysisResult, ...],
    *,
    config: ResolvedProjectConfiguration,
    repository: ArtifactRepository,
) -> AbsorptionAnalysisResult:
    stress = next((result for result in paired_results if result.analysis_label == analysis.stress_test_analysis), None)
    if stress is None:
        raise ValueError(f"Absorption analysis '{analysis.label}' lacks its stress-test source")
    reference_experiment, reference_label = _absorption_reference(analysis)
    _validate_absorption_contract(analysis, experiment, reference_experiment, config=config)
    reference_run = execution_run_id(reference_experiment, config.execution_fingerprint.value)
    reference_context = StageJobContext(experiment_id=reference_experiment)
    artifact = repository.read(
        f"runs/{reference_run.value}/{IdentityBuilder.statistical_analysis_job_id(reference_context).value}"
    )
    if not artifact.found or artifact.payload_bytes is None:
        raise ValueError(f"Absorption analysis '{analysis.label}' reference statistical artifact is unavailable")
    payload = json.loads(artifact.payload_bytes)
    if not isinstance(payload, list):
        raise ValueError(f"Absorption analysis '{analysis.label}' reference statistical artifact is malformed")
    reference = next(
        (item for item in payload if isinstance(item, dict) and item.get("analysis_label") == reference_label), None
    )
    if not isinstance(reference, dict):
        raise ValueError(f"Absorption analysis '{analysis.label}' reference analysis is unavailable")
    reference_seed_differences = reference.get("seed_differences")
    if not isinstance(reference_seed_differences, list) or not all(
        isinstance(value, (int, float)) for value in reference_seed_differences
    ):
        raise ValueError(f"Absorption analysis '{analysis.label}' reference analysis is malformed")
    return seed_ratio_result(
        label=analysis.label,
        formula=analysis.formula,
        numerator_seed_differences=stress.seed_differences,
        denominator_seed_differences=tuple(float(value) for value in reference_seed_differences),
        materiality_rule=analysis.denominator_materiality_rule,
        undefined_behavior=analysis.undefined_denominator_behavior,
    )


def _absorption_reference(analysis: AbsorptionAnalysisRecord) -> tuple[ExperimentId, str]:
    if not isinstance(analysis.reference_analysis, dict):
        raise ValueError(f"Absorption analysis '{analysis.label}' requires an explicit reference experiment")
    experiment = analysis.reference_analysis.get("experiment")
    label = analysis.reference_analysis.get("analysis")
    if not isinstance(experiment, str) or not isinstance(label, str):
        raise ValueError(f"Absorption analysis '{analysis.label}' reference is malformed")
    return (ExperimentId(experiment), label)


def _validate_absorption_contract(
    analysis: AbsorptionAnalysisRecord,
    experiment: ExperimentRecord,
    reference_experiment_id: ExperimentId,
    *,
    config: ResolvedProjectConfiguration,
) -> None:
    reference = config.experiments.get(reference_experiment_id)
    if experiment.seed_cohort_id != reference.seed_cohort_id:
        raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched training-seed cohort")
    if experiment.checkpoint_profile_id != reference.checkpoint_profile_id:
        raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched checkpoint profile")
    if experiment.eligibility_policy_id != reference.eligibility_policy_id:
        raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched eligibility policy")
    if experiment.population_ids != reference.population_ids:
        raise ValueError(f"Absorption analysis '{analysis.label}' has an unmatched client population")
    mapping = analysis.matching_contract.get("evaluation_label_mapping")
    if not isinstance(mapping, dict):
        raise ValueError(f"Absorption analysis '{analysis.label}' lacks an evaluation-label mapping")
    reference_mapping = mapping.get("reference")
    stress_mapping = mapping.get("stress_test")
    if not isinstance(reference_mapping, dict) or not isinstance(stress_mapping, dict):
        raise ValueError(f"Absorption analysis '{analysis.label}' has malformed evaluation-label mappings")
    _validate_evaluation_label_mapping(analysis.label, reference_mapping, stress_mapping, reference, experiment)


def _validate_evaluation_label_mapping(
    analysis_label: str,
    reference_mapping: dict,
    stress_mapping: dict,
    reference: ExperimentRecord,
    experiment: ExperimentRecord,
) -> None:
    for logical_label in ("shared_mean", "local"):
        reference_label = reference_mapping.get(logical_label)
        stress_label = stress_mapping.get(logical_label)
        if not isinstance(reference_label, str) or not isinstance(stress_label, str):
            raise ValueError(f"Absorption analysis '{analysis_label}' lacks '{logical_label}' label mappings")
        reference_evaluation = next((item for item in reference.evaluations if item.label == reference_label), None)
        stress_evaluation = next((item for item in experiment.evaluations if item.label == stress_label), None)
        if reference_evaluation is None or stress_evaluation is None:
            raise ValueError(f"Absorption analysis '{analysis_label}' maps an unavailable evaluation")
        if reference_evaluation.threshold_policy_id != stress_evaluation.threshold_policy_id:
            raise ValueError(f"Absorption analysis '{analysis_label}' has unmatched threshold policy semantics")
