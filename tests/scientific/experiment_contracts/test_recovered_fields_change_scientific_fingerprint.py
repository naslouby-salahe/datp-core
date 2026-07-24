from __future__ import annotations

import attrs

from datp_core.config.fingerprints import compute_fingerprint, unstructure_projection
from datp_core.config.resolve.experiments import _experiment_scientific_projection
from datp_core.core.identifiers import (
    CheckpointProfileId,
    EligibilityPolicyId,
    ExperimentId,
    PopulationId,
    SeedCohortId,
    StatisticalProfileId,
    ThresholdPolicyId,
    TrainingProfileId,
)
from datp_core.experiments.models import (
    AbsorptionAnalysisRecord,
    CapabilityRequirementRecord,
    EvaluationSpecRecord,
    EvidenceRole,
    ExperimentRecord,
    PrerequisiteSpecRecord,
    RunRequirement,
)


def _baseline_experiment() -> ExperimentRecord:
    return ExperimentRecord(
        identifier=ExperimentId("probe_experiment"),
        display_name="Probe Experiment",
        evidence_role=EvidenceRole.ANCHOR,
        run_requirement=RunRequirement.MANDATORY,
        population_ids=(PopulationId("probe_population"),),
        training_profile_id=TrainingProfileId("probe_training"),
        checkpoint_profile_id=CheckpointProfileId("probe_checkpoint"),
        seed_cohort_id=SeedCohortId("probe_seeds"),
        eligibility_policy_id=EligibilityPolicyId("probe_eligibility"),
        prerequisites=(PrerequisiteSpecRecord(experiment_id=ExperimentId("upstream"), required_outcome="succeeded"),),
        capability_requirements=(
            CapabilityRequirementRecord(
                capability="attack_sensitive_metrics",
                when_unavailable="suppress",
                applies_to_populations=(PopulationId("probe_population"),),
            ),
        ),
        evaluations=(
            EvaluationSpecRecord(
                label="primary",
                threshold_policy_id=ThresholdPolicyId("probe_policy"),
                run_requirement=RunRequirement.MANDATORY,
                overrides={"quantile": 0.95},
                population_id=PopulationId("probe_population"),
                recalibration_mode="none",
            ),
        ),
        analyses=(),
        report_ids=(),
        readiness_gates=(),
        validation_scope=None,
        never_promoted_to_confirmatory=None,
        outside_core_causal_ladder=None,
        faithful_reproduction_claim_forbidden=None,
        attack_sensitive_metrics_requested=None,
        unavailable_capability_reporting=(),
        independent_of_experiment=None,
        calibration_subset=None,
        method_naming_rule=None,
        personalization_parameter_selection_source=None,
        run_condition=None,
        unavailable_behavior=None,
        blocks_other_experiments_when_unavailable=None,
        estimate_basis=None,
        client_semantics_constraint=None,
        generalization_constraint=None,
        quantitative_claim_gate=None,
        population_equivalence_requirement=None,
        population_roles=None,
        scope_constraint=None,
        temporal_procedure={"boundary_index_formula": "floor(0.6 * n)"},
        primary_coefficient_selection=None,
        training_overrides=None,
    )


def _fingerprint_of(record: ExperimentRecord) -> str:
    return compute_fingerprint("scientific", _experiment_scientific_projection(record)).value


def test_evaluation_override_changes_scientific_fingerprint() -> None:
    baseline = _baseline_experiment()
    changed_override = attrs.evolve(
        baseline,
        evaluations=(attrs.evolve(baseline.evaluations[0], overrides={"quantile": 0.99}),),
    )
    assert _fingerprint_of(baseline) != _fingerprint_of(changed_override)


def test_prerequisite_required_outcome_changes_scientific_fingerprint() -> None:
    baseline = _baseline_experiment()
    changed_outcome = attrs.evolve(
        baseline,
        prerequisites=(PrerequisiteSpecRecord(experiment_id=ExperimentId("upstream"), required_outcome="failed"),),
    )
    assert _fingerprint_of(baseline) != _fingerprint_of(changed_outcome)


def test_capability_requirement_population_scope_changes_scientific_fingerprint() -> None:
    baseline = _baseline_experiment()
    changed_scope = attrs.evolve(
        baseline,
        capability_requirements=(
            attrs.evolve(
                baseline.capability_requirements[0],
                applies_to_populations=(PopulationId("a_different_population"),),
            ),
        ),
    )
    assert _fingerprint_of(baseline) != _fingerprint_of(changed_scope)


def test_temporal_procedure_changes_scientific_fingerprint() -> None:
    baseline = _baseline_experiment()
    changed_procedure = attrs.evolve(
        baseline,
        temporal_procedure={"boundary_index_formula": "floor(0.75 * n)"},
    )
    assert _fingerprint_of(baseline) != _fingerprint_of(changed_procedure)


def test_analysis_specific_contract_field_changes_scientific_fingerprint() -> None:
    def absorption_analysis(formula: str) -> AbsorptionAnalysisRecord:
        return AbsorptionAnalysisRecord(
            label="absorption",
            kind="absorption_analysis",
            result_type="absorption_result",
            statistical_profile=StatisticalProfileId("probe_profile"),
            absorption_metric="cv_fpr",
            formula=formula,
            band_interpretation="higher_is_better",
            denominator_materiality_rule="absolute_denominator_at_least_1.0e-6",
            undefined_denominator_behavior="suppress",
            matching_contract={"required_equal": ["dataset", "setup"]},
            outcome_bands=[{"name": "strong_retention", "condition": "absorption_ratio >= 0.75"}],
            outcome_bands_are_mutually_exclusive_and_exhaustive=True,
            reference_analysis={"experiment": "confirmatory", "analysis": "scope_effect"},
            stress_test_analysis="stress_scope_effect",
            alternative_path_rule=None,
        )

    baseline = absorption_analysis("1 - (cv_fpr_local / cv_fpr_shared)")
    perturbed = absorption_analysis("1 - (cv_fpr_shared / cv_fpr_local)")
    assert compute_fingerprint("scientific", unstructure_projection(baseline)) != compute_fingerprint(
        "scientific", unstructure_projection(perturbed)
    )


def test_display_name_metadata_change_does_not_change_scientific_fingerprint() -> None:
    baseline = _baseline_experiment()
    renamed = attrs.evolve(baseline, display_name="A Completely Different Display Name")
    assert _fingerprint_of(baseline) == _fingerprint_of(renamed)


def test_display_name_is_excluded_but_every_other_field_is_present_in_the_scientific_projection() -> None:
    projection = _experiment_scientific_projection(_baseline_experiment())
    assert "display_name" not in projection
    assert projection["temporal_procedure"] == {"boundary_index_formula": "floor(0.6 * n)"}
    assert isinstance(projection["prerequisites"], list)
    assert isinstance(projection["capability_requirements"], list)
    assert isinstance(projection["evaluations"], list)
    assert len(projection["prerequisites"]) == 1
    assert len(projection["capability_requirements"]) == 1
    assert len(projection["evaluations"]) == 1
