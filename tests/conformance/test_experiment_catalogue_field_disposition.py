"""Every authored experiment-catalogue leaf field has an explicit SCIENTIFIC / EXECUTION /
AUTHORING_METADATA disposition. This test introspects the live Pydantic model tree and compares
it against the _DISPOSITIONS table; it fails when a field is added, renamed, or removed without
a reviewed disposition decision.

Scope: AuthoredExperimentsCatalogueConfig only. Dataset/protocol/runtime extension is residual.
"""

from __future__ import annotations

import typing
from typing import Literal, get_args, get_origin

from pydantic import BaseModel

from datp_core.configuration.models import AuthoredExperimentsCatalogueConfig

Disposition = Literal["SCIENTIFIC", "EXECUTION", "AUTHORING_METADATA"]

# "."-delimited paths; repeated-container fields collapse to their field name.
_DISPOSITIONS: dict[str, Disposition] = {
    "schema_version": "EXECUTION",
    "study_populations.dataset": "SCIENTIFIC",
    "study_populations.setup": "SCIENTIFIC",
    "study_populations.metric_bundle": "SCIENTIFIC",
    "capabilities": "SCIENTIFIC",
    "suppression_behaviors": "SCIENTIFIC",
    "population_readiness_rule": "SCIENTIFIC",
    "analysis_conventions": "SCIENTIFIC",
    "eligibility_gates.candidate_population": "SCIENTIFIC",
    "eligibility_gates.minimum_benign_calibration_count": "SCIENTIFIC",
    "eligibility_gates.minimum_eligible_client_proportion": "SCIENTIFIC",
    "eligibility_gates.evaluation_time": "SCIENTIFIC",
    "eligibility_gates.failure_outcome": "SCIENTIFIC",
    "eligibility_gates.population_reduction_without_explicit_roadmap_authorization": "SCIENTIFIC",
    "eligibility_gates.applies_to_experiments": "SCIENTIFIC",
    "experiments.name": "SCIENTIFIC",
    "experiments.display_name": "AUTHORING_METADATA",
    "experiments.evidence_role": "SCIENTIFIC",
    "experiments.run_requirement": "SCIENTIFIC",
    "experiments.populations": "SCIENTIFIC",
    "experiments.training_profile": "SCIENTIFIC",
    "experiments.checkpoint_profile": "SCIENTIFIC",
    "experiments.seed_cohort": "SCIENTIFIC",
    "experiments.eligibility_policy": "SCIENTIFIC",
    "experiments.readiness_gates": "SCIENTIFIC",
    "experiments.prerequisites.experiment": "SCIENTIFIC",
    "experiments.prerequisites.required_outcome": "SCIENTIFIC",
    "experiments.capability_requirements.capability": "SCIENTIFIC",
    "experiments.capability_requirements.when_unavailable": "SCIENTIFIC",
    "experiments.capability_requirements.applies_to_populations": "SCIENTIFIC",
    "experiments.validation_scope": "SCIENTIFIC",
    "experiments.never_promoted_to_confirmatory": "SCIENTIFIC",
    "experiments.outside_core_causal_ladder": "SCIENTIFIC",
    "experiments.faithful_reproduction_claim_forbidden": "SCIENTIFIC",
    "experiments.attack_sensitive_metrics_requested": "SCIENTIFIC",
    "experiments.unavailable_capability_reporting": "SCIENTIFIC",
    "experiments.independent_of_experiment": "SCIENTIFIC",
    "experiments.sweeps.values": "SCIENTIFIC",
    "experiments.sweeps.conditions.name": "SCIENTIFIC",
    "experiments.sweeps.conditions.allocation": "SCIENTIFIC",
    "experiments.sweeps.conditions.dirichlet_alpha": "SCIENTIFIC",
    "experiments.calibration_subset.requested_sample_count": "SCIENTIFIC",
    "experiments.calibration_subset.selection_strategy": "SCIENTIFIC",
    "experiments.calibration_subset.nesting_policy": "SCIENTIFIC",
    "experiments.calibration_subset.nesting_rule": "SCIENTIFIC",
    "experiments.calibration_subset.selection_seed": "SCIENTIFIC",
    "experiments.calibration_subset.replicate_count": "SCIENTIFIC",
    "experiments.calibration_subset.replicate_seed_derivation": "SCIENTIFIC",
    "experiments.calibration_subset.model_retraining": "SCIENTIFIC",
    "experiments.calibration_subset.client_eligibility_per_requested_size": "SCIENTIFIC",
    "experiments.calibration_subset.subminimum_eligibility_policy": "SCIENTIFIC",
    "experiments.calibration_subset.subminimum_eligibility_policy_applies_to": "SCIENTIFIC",
    "experiments.calibration_subset.effective_eligibility_policy_by_sweep_condition": "SCIENTIFIC",
    "experiments.calibration_subset.insufficient_row_policy": "SCIENTIFIC",
    "experiments.calibration_subset.replicate_aggregation_within_seed": "SCIENTIFIC",
    "experiments.calibration_subset.seed_level_statistic": "SCIENTIFIC",
    "experiments.calibration_subset.additional_seed_level_statistic": "SCIENTIFIC",
    "experiments.calibration_subset.independent_inferential_unit": "SCIENTIFIC",
    "experiments.calibration_subset.replicates_counted_as_seeds": "SCIENTIFIC",
    "experiments.calibration_subset.full_calibration_reference_condition": "SCIENTIFIC",
    "experiments.evaluations.label": "SCIENTIFIC",
    "experiments.evaluations.threshold_policy": "SCIENTIFIC",
    "experiments.evaluations.overrides": "SCIENTIFIC",
    "experiments.evaluations.run_requirement": "SCIENTIFIC",
    "experiments.evaluations.population": "SCIENTIFIC",
    "experiments.evaluations.recalibration_mode": "SCIENTIFIC",
    "experiments.analyses.label": "SCIENTIFIC",
    "experiments.analyses.kind": "SCIENTIFIC",
    "experiments.analyses.result_type": "SCIENTIFIC",
    "experiments.analyses.first_evaluation": "SCIENTIFIC",
    "experiments.analyses.second_evaluation": "SCIENTIFIC",
    "experiments.analyses.source_evaluations": "SCIENTIFIC",
    "experiments.analyses.source_evaluation": "SCIENTIFIC",
    "experiments.analyses.reference_evaluation": "SCIENTIFIC",
    "experiments.analyses.source_analysis": "SCIENTIFIC",
    "experiments.analyses.numerator_analysis": "SCIENTIFIC",
    "experiments.analyses.denominator_analysis": "SCIENTIFIC",
    "experiments.analyses.denominator_composition": "SCIENTIFIC",
    "experiments.analyses.primary_metric": "SCIENTIFIC",
    "experiments.analyses.predictor_metric": "SCIENTIFIC",
    "experiments.analyses.outcome_metric": "SCIENTIFIC",
    "experiments.analyses.outcome_source_analysis": "SCIENTIFIC",
    "experiments.analyses.grouping_dimension": "SCIENTIFIC",
    "experiments.analyses.delta_orientation": "SCIENTIFIC",
    "experiments.analyses.delta_interpretation": "SCIENTIFIC",
    "experiments.analyses.required_direction": "SCIENTIFIC",
    "experiments.analyses.comparison_mode": "SCIENTIFIC",
    "experiments.analyses.comparison_mode_rule": "SCIENTIFIC",
    "experiments.analyses.comparison_unit": "SCIENTIFIC",
    "experiments.analyses.produced_fields": "SCIENTIFIC",
    "experiments.analyses.field_formulas": "SCIENTIFIC",
    "experiments.analyses.locked_client_identifier": "SCIENTIFIC",
    "experiments.analyses.per_sweep_cell": "SCIENTIFIC",
    "experiments.analyses.ordering_inversion_reporting": "SCIENTIFIC",
    "experiments.analyses.monotonicity_required": "SCIENTIFIC",
    "experiments.analyses.interpretation_constraint": "SCIENTIFIC",
    "experiments.analyses.formula": "SCIENTIFIC",
    "experiments.analyses.undefined_denominator_behavior": "SCIENTIFIC",
    "experiments.analyses.denominator_materiality_rule": "SCIENTIFIC",
    "experiments.analyses.target_coverage": "SCIENTIFIC",
    "experiments.analyses.coverage_direction": "SCIENTIFIC",
    "experiments.analyses.oracle_reference": "SCIENTIFIC",
    "experiments.analyses.statistical_fallback_requirements": "SCIENTIFIC",
    "experiments.analyses.historical_reference": "SCIENTIFIC",
    "experiments.analyses.interval_width_tolerance_multiplier": "SCIENTIFIC",
    "experiments.analyses.floating_point_tolerance": "SCIENTIFIC",
    "experiments.analyses.failure_reasons": "SCIENTIFIC",
    "experiments.analyses.downstream_blocking_behavior": "SCIENTIFIC",
    "experiments.analyses.full_curve_reporting": "SCIENTIFIC",
    "experiments.analyses.post_hoc_weight_selection": "SCIENTIFIC",
    "experiments.analyses.statistical_profile": "SCIENTIFIC",
    "experiments.analyses.secondary_statistical_profile": "SCIENTIFIC",
    "experiments.analyses.run_requirement": "SCIENTIFIC",
    "experiments.analyses.reference_analysis": "SCIENTIFIC",
    "experiments.analyses.stress_test_analysis": "SCIENTIFIC",
    "experiments.analyses.absorption_metric": "SCIENTIFIC",
    "experiments.analyses.matching_contract": "SCIENTIFIC",
    "experiments.analyses.outcome_bands": "SCIENTIFIC",
    "experiments.analyses.outcome_bands_are_mutually_exclusive_and_exhaustive": "SCIENTIFIC",
    "experiments.analyses.alternative_path_rule": "SCIENTIFIC",
    "experiments.analyses.band_interpretation": "SCIENTIFIC",
    "experiments.analyses.required_operational_input": "SCIENTIFIC",
    "experiments.analyses.per_client_reporting_required": "SCIENTIFIC",
    "experiments.analyses.unavailable_behavior": "SCIENTIFIC",
    "experiments.analyses.estimate_basis": "SCIENTIFIC",
    "experiments.analyses.static_reference_evaluation": "SCIENTIFIC",
    "experiments.analyses.frozen_evaluation": "SCIENTIFIC",
    "experiments.analyses.recalibrated_evaluation": "SCIENTIFIC",
    "experiments.analyses.recovery_fields": "SCIENTIFIC",
    "experiments.analyses.drift_excess_formula": "SCIENTIFIC",
    "experiments.analyses.recovered_amount_formula": "SCIENTIFIC",
    "experiments.analyses.recovery_ratio_formula": "SCIENTIFIC",
    "experiments.analyses.meaningful_degradation_rule": "SCIENTIFIC",
    "experiments.analyses.recovery_ratio_precondition": "SCIENTIFIC",
    "experiments.analyses.negative_recovery_policy": "SCIENTIFIC",
    "experiments.analyses.recovery_ratio_direction": "SCIENTIFIC",
    "experiments.analyses.meaningful_recovery_threshold": "SCIENTIFIC",
    "experiments.analyses.chronology_unverifiable_policy": "SCIENTIFIC",
    "experiments.reports": "SCIENTIFIC",
    "experiments.method_naming_rule": "SCIENTIFIC",
    "experiments.personalization_parameter_selection_source": "SCIENTIFIC",
    "experiments.run_condition": "SCIENTIFIC",
    "experiments.unavailable_behavior": "SCIENTIFIC",
    "experiments.blocks_other_experiments_when_unavailable": "SCIENTIFIC",
    "experiments.estimate_basis": "SCIENTIFIC",
    "experiments.client_semantics_constraint": "SCIENTIFIC",
    "experiments.generalization_constraint": "SCIENTIFIC",
    "experiments.quantitative_claim_gate": "SCIENTIFIC",
    "experiments.population_equivalence_requirement": "SCIENTIFIC",
    "experiments.population_roles": "SCIENTIFIC",
    "experiments.scope_constraint": "SCIENTIFIC",
    "experiments.temporal_procedure": "SCIENTIFIC",
    "experiments.primary_coefficient_selection": "SCIENTIFIC",
    "experiments.training_overrides": "SCIENTIFIC",
}


def _is_model_type(candidate: object) -> bool:
    return isinstance(candidate, type) and issubclass(candidate, BaseModel)


def _nested_models(annotation: object) -> list[type[BaseModel]]:
    """Find every BaseModel subtype reachable from an annotation (through Optional/list/dict/Union)."""
    if _is_model_type(annotation):
        return [annotation]  # type: ignore[list-item]
    origin = get_origin(annotation)
    if origin is None:
        return []
    found: list[type[BaseModel]] = []
    for arg in get_args(annotation):
        found.extend(_nested_models(arg))
    return found


def _leaf_paths(model: type[BaseModel], prefix: str, seen: frozenset[type[BaseModel]]) -> set[str]:
    if model in seen:
        return set()
    seen = seen | {model}
    paths: set[str] = set()
    for field_name, field_info in model.model_fields.items():
        full_path = f"{prefix}.{field_name}" if prefix else field_name
        nested = _nested_models(field_info.annotation)
        if nested:
            for nested_model in nested:
                paths |= _leaf_paths(nested_model, full_path, seen)
        else:
            paths.add(full_path)
    return paths


def test_every_authored_experiment_catalogue_field_has_an_explicit_disposition() -> None:
    actual_paths = _leaf_paths(AuthoredExperimentsCatalogueConfig, "", frozenset())
    declared_paths = set(_DISPOSITIONS)

    undeclared = sorted(actual_paths - declared_paths)
    stale = sorted(declared_paths - actual_paths)

    assert not undeclared, (
        f"Authored field path(s) with no disposition classification: {undeclared}. "
        "Every field must be classified SCIENTIFIC, EXECUTION, or AUTHORING_METADATA in "
        "_DISPOSITIONS before it may be added to experiments.yaml's schema."
    )
    assert not stale, (
        f"_DISPOSITIONS has entries for field path(s) no longer present on the authored model: {stale}. "
        "Remove them (the field was renamed or deleted)."
    )


def test_disposition_table_only_uses_declared_literal_values() -> None:
    allowed = set(typing.get_args(Disposition))
    offenders = {path: value for path, value in _DISPOSITIONS.items() if value not in allowed}
    assert not offenders, f"Invalid disposition value(s): {offenders}"
