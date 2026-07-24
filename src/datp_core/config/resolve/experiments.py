"""Experiment-resolution functions extracted from the monolithic resolver.

Ownership boundary: converts authored experiment Pydantic models into immutable
domain records owned by ``experiments/models.py``. Exports a narrow function surface;
does not import pipeline execution, CLI, or infrastructure.
"""

from __future__ import annotations

from typing import cast

from attrs import define

from datp_core.config.fingerprints import unstructure_projection
from datp_core.config.loading import ConfigurationError
from datp_core.config.schema.experiments import (
    AnalysisSpecConfig,
    AuthoredExperimentConfig,
    AuthoredExperimentsCatalogueConfig,
    SweepVariableConfig,
)
from datp_core.core.identifiers import (
    CheckpointProfileId,
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    ExperimentId,
    MetricBundleId,
    PopulationId,
    SeedCohortId,
    StatisticalProfileId,
    ThresholdPolicyId,
    TrainingProfileId,
)
from datp_core.core.values import PositiveInt, Probability, RecalibrationMode, Seed, TypedDomainRegistry
from datp_core.data.contracts import ResolvedDataset
from datp_core.experiments.models import (
    AbsorptionAnalysisRecord,
    AlertBurdenAnalysisRecord,
    AnalysisKind,
    AnalysisRecord,
    AnchorEquivalenceAnalysisRecord,
    CalibrationSubsetRecord,
    CapabilityRequirementRecord,
    ClusterStabilityAnalysisRecord,
    ConditionSweepRecord,
    ConformalCoverageAnalysisRecord,
    DistributionMechanismAnalysisRecord,
    EligibilityGateRecord,
    EvaluationSpecRecord,
    EvidenceRole,
    ExperimentRecord,
    LockedClientDistributionAnalysisRecord,
    MetricAssociationAnalysisRecord,
    PairedThresholdAnalysisRecord,
    PopulationRecord,
    PrerequisiteSpecRecord,
    QuantileEstimationAnalysisRecord,
    RecoveryFractionAnalysisRecord,
    ResourceCostAnalysisRecord,
    RunRequirement,
    SweepConditionAllocation,
    SweepConditionRecord,
    SweepRecord,
    SweepValue,
    TemporalRecoveryAnalysisRecord,
    ThresholdStabilityAnalysisRecord,
    ValueSweepRecord,
)
from datp_core.thresholding.models import ThresholdPolicyRecord


def _experiment_scientific_projection(record: ExperimentRecord) -> dict[str, object]:
    """Unstructure an experiment for the scientific fingerprint, excluding display-only prose.

    `display_name` is authored human-readable prose with no bearing on what is executed, evaluated,
    or claimed; it is the one field in `AuthoredExperimentConfig` classified AUTHORING_METADATA.
    """
    projected = cast(dict, unstructure_projection(record))
    del projected["display_name"]
    return projected


def _resolve_sweep_value(value: object) -> SweepValue:
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            raise ConfigurationError(f"Sweep value list must contain only strings, got: {value!r}")
        return tuple(value)
    if isinstance(value, str | int | float):
        return value
    raise ConfigurationError(f"Unsupported authored sweep value: {value!r}")


def _resolve_sweep(name: str, cfg: SweepVariableConfig) -> SweepRecord:
    if cfg.values is not None:
        return ValueSweepRecord(name=name, values=tuple(_resolve_sweep_value(value) for value in cfg.values))
    assert cfg.conditions is not None  # enforced by SweepVariableConfig.validate_exactly_one_variant
    return ConditionSweepRecord(
        name=name,
        conditions=tuple(
            SweepConditionRecord(
                name=c.name, allocation=SweepConditionAllocation(c.allocation), dirichlet_alpha=c.dirichlet_alpha
            )
            for c in cfg.conditions
        ),
    )


def _require(value: object | None, *, experiment_name: str, analysis_label: str, field_name: str) -> object:
    if value is None:
        raise ConfigurationError(
            f"Experiment '{experiment_name}' analysis '{analysis_label}' is missing required field '{field_name}'"
        )
    return value


def _tuple_str_list(value: object) -> tuple[str, ...]:
    """Deduplicated single authoritative cast: 'list[str]' → tuple[str, ...] (S1192)."""
    return tuple(cast("list[str]", value))


def _build_paired_threshold_analysis_record(
    exp_name: str,
    a: AnalysisSpecConfig,
    statistical_profile: StatisticalProfileId,
    secondary_statistical_profile: StatisticalProfileId | None,
) -> PairedThresholdAnalysisRecord:
    return PairedThresholdAnalysisRecord(
        label=a.label,
        kind=a.kind,
        result_type=a.result_type,
        statistical_profile=statistical_profile,
        secondary_statistical_profile=secondary_statistical_profile,
        first_evaluation=cast(
            str,
            _require(
                a.first_evaluation,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="first_evaluation",
            ),
        ),
        second_evaluation=cast(
            str,
            _require(
                a.second_evaluation,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="second_evaluation",
            ),
        ),
        primary_metric=cast(
            str,
            _require(
                a.primary_metric,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="primary_metric",
            ),
        ),
        delta_orientation=cast(
            str,
            _require(
                a.delta_orientation,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="delta_orientation",
            ),
        ),
        delta_interpretation=cast(
            str,
            _require(
                a.delta_interpretation,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="delta_interpretation",
            ),
        ),
        required_direction=a.required_direction,
        monotonicity_required=a.monotonicity_required,
        ordering_inversion_reporting=a.ordering_inversion_reporting,
        per_sweep_cell=a.per_sweep_cell,
        full_curve_reporting=a.full_curve_reporting,
        post_hoc_weight_selection=a.post_hoc_weight_selection,
    )


def _build_temporal_recovery_analysis_record(
    exp_name: str,
    a: AnalysisSpecConfig,
    statistical_profile: StatisticalProfileId,
) -> TemporalRecoveryAnalysisRecord:
    return TemporalRecoveryAnalysisRecord(
        label=a.label,
        kind=a.kind,
        result_type=a.result_type,
        statistical_profile=statistical_profile,
        primary_metric=cast(
            str,
            _require(
                a.primary_metric,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="primary_metric",
            ),
        ),
        static_reference_evaluation=cast(
            str,
            _require(
                a.static_reference_evaluation,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="static_reference_evaluation",
            ),
        ),
        frozen_evaluation=cast(
            str,
            _require(
                a.frozen_evaluation,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="frozen_evaluation",
            ),
        ),
        recalibrated_evaluation=cast(
            str,
            _require(
                a.recalibrated_evaluation,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="recalibrated_evaluation",
            ),
        ),
        recovery_fields=_tuple_str_list(
            _require(
                a.recovery_fields,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="recovery_fields",
            )
        ),
        drift_excess_formula=cast(
            str,
            _require(
                a.drift_excess_formula,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="drift_excess_formula",
            ),
        ),
        recovered_amount_formula=cast(
            str,
            _require(
                a.recovered_amount_formula,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="recovered_amount_formula",
            ),
        ),
        recovery_ratio_formula=cast(
            str,
            _require(
                a.recovery_ratio_formula,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="recovery_ratio_formula",
            ),
        ),
        meaningful_degradation_rule=cast(
            str,
            _require(
                a.meaningful_degradation_rule,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="meaningful_degradation_rule",
            ),
        ),
        recovery_ratio_precondition=cast(
            str,
            _require(
                a.recovery_ratio_precondition,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="recovery_ratio_precondition",
            ),
        ),
        negative_recovery_policy=cast(
            str,
            _require(
                a.negative_recovery_policy,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="negative_recovery_policy",
            ),
        ),
        recovery_ratio_direction=cast(
            str,
            _require(
                a.recovery_ratio_direction,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="recovery_ratio_direction",
            ),
        ),
        meaningful_recovery_threshold=cast(
            float,
            _require(
                a.meaningful_recovery_threshold,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="meaningful_recovery_threshold",
            ),
        ),
        chronology_unverifiable_policy=cast(
            str,
            _require(
                a.chronology_unverifiable_policy,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="chronology_unverifiable_policy",
            ),
        ),
        outcome_bands=cast(
            list,
            _require(
                a.outcome_bands,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="outcome_bands",
            ),
        ),
        outcome_bands_are_mutually_exclusive_and_exhaustive=cast(
            bool,
            _require(
                a.outcome_bands_are_mutually_exclusive_and_exhaustive,
                experiment_name=exp_name,
                analysis_label=a.label,
                field_name="outcome_bands_are_mutually_exclusive_and_exhaustive",
            ),
        ),
    )


def _resolve_analysis(exp_cfg: AuthoredExperimentConfig, a: AnalysisSpecConfig) -> AnalysisRecord:
    def req(field_name: str) -> object:
        return _require(
            getattr(a, field_name), experiment_name=exp_cfg.name, analysis_label=a.label, field_name=field_name
        )

    statistical_profile = StatisticalProfileId(cast(str, req("statistical_profile")))
    secondary_statistical_profile = (
        StatisticalProfileId(a.secondary_statistical_profile) if a.secondary_statistical_profile is not None else None
    )
    try:
        kind = AnalysisKind(a.kind)
    except ValueError as error:
        raise ConfigurationError(
            f"Experiment '{exp_cfg.name}' analysis '{a.label}' has unsupported kind '{a.kind}'"
        ) from error

    match kind:
        case AnalysisKind.PAIRED_THRESHOLD:
            return _build_paired_threshold_analysis_record(
                exp_cfg.name, a, statistical_profile, secondary_statistical_profile
            )
        case AnalysisKind.ABSORPTION:
            return AbsorptionAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                absorption_metric=cast(str, req("absorption_metric")),
                formula=cast(str, req("formula")),
                band_interpretation=cast(str, req("band_interpretation")),
                denominator_materiality_rule=cast("float | str", req("denominator_materiality_rule")),
                undefined_denominator_behavior=cast(str, req("undefined_denominator_behavior")),
                matching_contract=cast(dict, req("matching_contract")),
                outcome_bands=cast(list, req("outcome_bands")),
                outcome_bands_are_mutually_exclusive_and_exhaustive=cast(
                    bool, req("outcome_bands_are_mutually_exclusive_and_exhaustive")
                ),
                reference_analysis=cast("str | dict", req("reference_analysis")),
                stress_test_analysis=cast(str, req("stress_test_analysis")),
                alternative_path_rule=a.alternative_path_rule,
            )
        case AnalysisKind.ALERT_BURDEN:
            return AlertBurdenAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                formula=cast(str, req("formula")),
                produced_fields=_tuple_str_list(req("produced_fields")),
                source_evaluations=_tuple_str_list(req("source_evaluations")),
                required_operational_input=cast(str, req("required_operational_input")),
                per_client_reporting_required=cast(bool, req("per_client_reporting_required")),
                unavailable_behavior=cast(str, req("unavailable_behavior")),
            )
        case AnalysisKind.ANCHOR_EQUIVALENCE:
            return AnchorEquivalenceAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                source_analysis=cast(str, req("source_analysis")),
                comparison_mode=cast(str, req("comparison_mode")),
                comparison_mode_rule=cast(str, req("comparison_mode_rule")),
                interval_width_tolerance_multiplier=cast(float, req("interval_width_tolerance_multiplier")),
                floating_point_tolerance=cast("dict[str, float]", req("floating_point_tolerance")),
                historical_reference=cast("dict[str, float | str]", req("historical_reference")),
                statistical_fallback_requirements=_tuple_str_list(req("statistical_fallback_requirements")),
                failure_reasons=_tuple_str_list(req("failure_reasons")),
                downstream_blocking_behavior=cast(str, req("downstream_blocking_behavior")),
            )
        case AnalysisKind.CLUSTER_STABILITY:
            return ClusterStabilityAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                source_evaluation=cast(str, req("source_evaluation")),
                comparison_unit=cast(str, req("comparison_unit")),
                produced_fields=_tuple_str_list(req("produced_fields")),
                reference_evaluation=a.reference_evaluation,
                run_requirement=(RunRequirement(a.run_requirement) if a.run_requirement is not None else None),
            )
        case AnalysisKind.CONFORMAL_COVERAGE:
            return ConformalCoverageAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                source_evaluation=cast(str, req("source_evaluation")),
                target_coverage=cast(float, req("target_coverage")),
                produced_fields=_tuple_str_list(req("produced_fields")),
                coverage_direction=a.coverage_direction,
            )
        case AnalysisKind.DISTRIBUTION_MECHANISM:
            return DistributionMechanismAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                source_evaluations=_tuple_str_list(req("source_evaluations")),
                produced_fields=_tuple_str_list(req("produced_fields")),
                field_formulas=a.field_formulas,
            )
        case AnalysisKind.LOCKED_CLIENT_DISTRIBUTION:
            return LockedClientDistributionAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                source_evaluations=_tuple_str_list(req("source_evaluations")),
                produced_fields=_tuple_str_list(req("produced_fields")),
                locked_client_identifier=cast(str, req("locked_client_identifier")),
            )
        case AnalysisKind.METRIC_ASSOCIATION:
            return MetricAssociationAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                secondary_statistical_profile=secondary_statistical_profile,
                predictor_metric=cast(str, req("predictor_metric")),
                outcome_metric=cast(str, req("outcome_metric")),
                outcome_source_analysis=cast(str, req("outcome_source_analysis")),
                interpretation_constraint=cast(str, req("interpretation_constraint")),
                grouping_dimension=a.grouping_dimension,
            )
        case AnalysisKind.QUANTILE_ESTIMATION:
            return QuantileEstimationAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                source_evaluations=_tuple_str_list(req("source_evaluations")),
                produced_fields=_tuple_str_list(req("produced_fields")),
                oracle_reference=cast(str, req("oracle_reference")),
            )
        case AnalysisKind.RECOVERY_FRACTION:
            return RecoveryFractionAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                formula=cast(str, req("formula")),
                numerator_analysis=cast(str, req("numerator_analysis")),
                denominator_analysis=cast(str, req("denominator_analysis")),
                denominator_composition=cast(str, req("denominator_composition")),
                denominator_materiality_rule=cast("float | str", req("denominator_materiality_rule")),
                undefined_denominator_behavior=cast(str, req("undefined_denominator_behavior")),
            )
        case AnalysisKind.RESOURCE_COST:
            return ResourceCostAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                source_evaluations=_tuple_str_list(req("source_evaluations")),
                produced_fields=_tuple_str_list(req("produced_fields")),
                estimate_basis=cast(str, req("estimate_basis")),
            )
        case AnalysisKind.TEMPORAL_RECOVERY:
            return _build_temporal_recovery_analysis_record(exp_cfg.name, a, statistical_profile)
        case AnalysisKind.THRESHOLD_STABILITY:
            return ThresholdStabilityAnalysisRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                statistical_profile=statistical_profile,
                source_evaluation=cast(str, req("source_evaluation")),
                produced_fields=_tuple_str_list(req("produced_fields")),
                per_sweep_cell=cast(str, req("per_sweep_cell")),
            )


@define(frozen=True, slots=True, kw_only=True)
class ResolvedExperimentCatalogue:
    """Every immutable record resolved from the authored experiment catalogue document (experiments.yaml)."""

    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    capabilities: tuple[str, ...]
    suppression_behaviors: tuple[str, ...]
    population_readiness_rule: dict[str, str | bool]
    eligibility_gates: TypedDomainRegistry[str, EligibilityGateRecord]
    analysis_conventions: dict[str, str]


def _resolve_populations(
    authored_experiments: AuthoredExperimentsCatalogueConfig,
    resolved_datasets: dict[DatasetId, ResolvedDataset],
) -> dict[PopulationId, PopulationRecord]:
    populations_dict: dict[PopulationId, PopulationRecord] = {}
    for pop_key, pop_cfg in authored_experiments.study_populations.items():
        pop_id = PopulationId(pop_key)
        target_dataset_id = DatasetId(pop_cfg.dataset)
        if target_dataset_id not in resolved_datasets:
            raise ConfigurationError(f"Population '{pop_key}' references unregistered dataset '{pop_cfg.dataset}'")
        dataset_obj = resolved_datasets[target_dataset_id]
        setup_id = DatasetSetupId(pop_cfg.setup)
        if not any(setup.identifier == setup_id for setup in dataset_obj.setups):
            raise ConfigurationError(
                f"Population '{pop_key}' references unregistered setup '{pop_cfg.setup}' in dataset '{pop_cfg.dataset}'"
            )
        metric_bundle_id = MetricBundleId(pop_cfg.metric_bundle)
        populations_dict[pop_id] = PopulationRecord(
            identifier=pop_id,
            dataset_id=target_dataset_id,
            setup_id=setup_id,
            metric_bundle_id=metric_bundle_id,
        )
    return populations_dict


def _resolve_eligibility_gates(
    authored_experiments: AuthoredExperimentsCatalogueConfig,
) -> dict[str, EligibilityGateRecord]:
    eligibility_gates_dict: dict[str, EligibilityGateRecord] = {}
    for gate_key, gate_cfg in authored_experiments.eligibility_gates.items():
        eligibility_gates_dict[gate_key] = EligibilityGateRecord(
            identifier=gate_key,
            candidate_population=gate_cfg.candidate_population,
            minimum_benign_calibration_count=PositiveInt(gate_cfg.minimum_benign_calibration_count),
            minimum_eligible_client_proportion=Probability(gate_cfg.minimum_eligible_client_proportion),
            evaluation_time=gate_cfg.evaluation_time,
            failure_outcome=gate_cfg.failure_outcome,
            population_reduction_without_explicit_roadmap_authorization=(
                gate_cfg.population_reduction_without_explicit_roadmap_authorization
            ),
            applies_to_experiments=tuple(ExperimentId(e) for e in gate_cfg.applies_to_experiments),
        )
    return eligibility_gates_dict


def _resolve_experiment_evaluations(
    exp_cfg: AuthoredExperimentConfig,
    threshold_policies: dict[ThresholdPolicyId, ThresholdPolicyRecord],
    populations_dict: dict[PopulationId, PopulationRecord],
) -> list[EvaluationSpecRecord]:
    evals_list = []
    for ev in exp_cfg.evaluations:
        tp_id = ThresholdPolicyId(ev.threshold_policy)
        if tp_id not in threshold_policies:
            raise ConfigurationError(
                f"Experiment '{exp_cfg.name}' evaluation '{ev.label}' references "
                f"unregistered threshold policy '{ev.threshold_policy}'"
            )
        eval_population_id = PopulationId(ev.population) if ev.population is not None else None
        if eval_population_id is not None and eval_population_id not in populations_dict:
            raise ConfigurationError(
                f"Experiment '{exp_cfg.name}' evaluation '{ev.label}' references "
                f"unregistered population '{ev.population}'"
            )
        evals_list.append(
            EvaluationSpecRecord(
                label=ev.label,
                threshold_policy_id=tp_id,
                run_requirement=(
                    RunRequirement(ev.run_requirement) if ev.run_requirement else RunRequirement.MANDATORY
                ),
                overrides=ev.overrides,
                population_id=eval_population_id,
                recalibration_mode=(
                    RecalibrationMode(ev.recalibration_mode) if ev.recalibration_mode is not None else None
                ),
            )
        )
    return evals_list


def _resolve_experiment_capability_requirements(
    exp_cfg: AuthoredExperimentConfig,
    populations_dict: dict[PopulationId, PopulationRecord],
) -> list[CapabilityRequirementRecord]:
    capability_requirements_list = []
    for requirement in exp_cfg.capability_requirements:
        applies_to_population_ids = (
            tuple(PopulationId(p) for p in requirement.applies_to_populations)
            if requirement.applies_to_populations is not None
            else None
        )
        if applies_to_population_ids is not None:
            for pop_id in applies_to_population_ids:
                if pop_id not in populations_dict:
                    raise ConfigurationError(
                        f"Experiment '{exp_cfg.name}' capability requirement '{requirement.capability}' "
                        f"references unregistered population '{pop_id}'"
                    )
        capability_requirements_list.append(
            CapabilityRequirementRecord(
                capability=requirement.capability,
                when_unavailable=requirement.when_unavailable,
                applies_to_populations=applies_to_population_ids,
            )
        )
    return capability_requirements_list


def _resolve_calibration_subset(exp_cfg: AuthoredExperimentConfig) -> CalibrationSubsetRecord | None:
    cs = exp_cfg.calibration_subset
    if cs is None:
        return None
    return CalibrationSubsetRecord(
        requested_sample_count=cs.requested_sample_count,
        selection_strategy=cs.selection_strategy,
        nesting_policy=cs.nesting_policy,
        nesting_rule=cs.nesting_rule,
        selection_seed=Seed(cs.selection_seed),
        replicate_count=PositiveInt(cs.replicate_count),
        replicate_seed_derivation=cs.replicate_seed_derivation,
        model_retraining=cs.model_retraining,
        client_eligibility_per_requested_size=cs.client_eligibility_per_requested_size,
        subminimum_eligibility_policy=cs.subminimum_eligibility_policy,
        subminimum_eligibility_policy_applies_to=cs.subminimum_eligibility_policy_applies_to,
        effective_eligibility_policy_by_sweep_condition=cs.effective_eligibility_policy_by_sweep_condition,
        insufficient_row_policy=cs.insufficient_row_policy,
        replicate_aggregation_within_seed=cs.replicate_aggregation_within_seed,
        seed_level_statistic=cs.seed_level_statistic,
        additional_seed_level_statistic=cs.additional_seed_level_statistic,
        independent_inferential_unit=cs.independent_inferential_unit,
        replicates_counted_as_seeds=cs.replicates_counted_as_seeds,
        full_calibration_reference_condition=cs.full_calibration_reference_condition,
    )


def _resolve_experiment(
    exp_cfg: AuthoredExperimentConfig,
    threshold_policies: dict[ThresholdPolicyId, ThresholdPolicyRecord],
    populations_dict: dict[PopulationId, PopulationRecord],
) -> ExperimentRecord:
    exp_id = ExperimentId(exp_cfg.name)
    evals_list = _resolve_experiment_evaluations(exp_cfg, threshold_policies, populations_dict)
    analyses_list = [_resolve_analysis(exp_cfg, a) for a in exp_cfg.analyses]
    capability_requirements_list = _resolve_experiment_capability_requirements(exp_cfg, populations_dict)
    return ExperimentRecord(
        identifier=exp_id,
        display_name=exp_cfg.display_name,
        evidence_role=EvidenceRole(exp_cfg.evidence_role),
        run_requirement=RunRequirement(exp_cfg.run_requirement),
        population_ids=tuple(PopulationId(p) for p in exp_cfg.populations),
        training_profile_id=TrainingProfileId(exp_cfg.training_profile),
        checkpoint_profile_id=CheckpointProfileId(exp_cfg.checkpoint_profile),
        seed_cohort_id=SeedCohortId(exp_cfg.seed_cohort),
        eligibility_policy_id=EligibilityPolicyId(exp_cfg.eligibility_policy),
        prerequisites=tuple(
            PrerequisiteSpecRecord(experiment_id=ExperimentId(p.experiment), required_outcome=p.required_outcome)
            for p in exp_cfg.prerequisites
        ),
        capability_requirements=tuple(capability_requirements_list),
        evaluations=tuple(evals_list),
        analyses=tuple(analyses_list),
        report_ids=tuple(exp_cfg.reports),
        sweeps=(
            tuple(_resolve_sweep(name, sweep) for name, sweep in sorted(exp_cfg.sweeps.items()))
            if exp_cfg.sweeps is not None
            else ()
        ),
        readiness_gates=tuple(exp_cfg.readiness_gates),
        validation_scope=exp_cfg.validation_scope,
        never_promoted_to_confirmatory=exp_cfg.never_promoted_to_confirmatory,
        outside_core_causal_ladder=exp_cfg.outside_core_causal_ladder,
        faithful_reproduction_claim_forbidden=exp_cfg.faithful_reproduction_claim_forbidden,
        attack_sensitive_metrics_requested=exp_cfg.attack_sensitive_metrics_requested,
        unavailable_capability_reporting=tuple(exp_cfg.unavailable_capability_reporting),
        independent_of_experiment=(
            ExperimentId(exp_cfg.independent_of_experiment) if exp_cfg.independent_of_experiment is not None else None
        ),
        calibration_subset=_resolve_calibration_subset(exp_cfg),
        method_naming_rule=exp_cfg.method_naming_rule,
        personalization_parameter_selection_source=exp_cfg.personalization_parameter_selection_source,
        run_condition=exp_cfg.run_condition,
        unavailable_behavior=exp_cfg.unavailable_behavior,
        blocks_other_experiments_when_unavailable=exp_cfg.blocks_other_experiments_when_unavailable,
        estimate_basis=exp_cfg.estimate_basis,
        client_semantics_constraint=exp_cfg.client_semantics_constraint,
        generalization_constraint=exp_cfg.generalization_constraint,
        quantitative_claim_gate=exp_cfg.quantitative_claim_gate,
        population_equivalence_requirement=exp_cfg.population_equivalence_requirement,
        population_roles=exp_cfg.population_roles,
        scope_constraint=exp_cfg.scope_constraint,
        temporal_procedure=exp_cfg.temporal_procedure,
        primary_coefficient_selection=exp_cfg.primary_coefficient_selection,
        training_overrides=exp_cfg.training_overrides,
    )


def resolve_experiment_catalogue(
    authored_experiments: AuthoredExperimentsCatalogueConfig,
    resolved_datasets: dict[DatasetId, ResolvedDataset],
    threshold_policies: dict[ThresholdPolicyId, ThresholdPolicyRecord],
) -> ResolvedExperimentCatalogue:
    """Resolve the authored experiment catalogue document (experiments.yaml) into immutable records."""
    populations_dict = _resolve_populations(authored_experiments, resolved_datasets)
    eligibility_gates_dict = _resolve_eligibility_gates(authored_experiments)

    experiments_dict: dict[ExperimentId, ExperimentRecord] = {}
    for exp_cfg in authored_experiments.experiments:
        exp_id = ExperimentId(exp_cfg.name)
        if exp_id in experiments_dict:
            raise ConfigurationError(f"Duplicate experiment identifier: '{exp_cfg.name}'")
        experiments_dict[exp_id] = _resolve_experiment(exp_cfg, threshold_policies, populations_dict)

    return ResolvedExperimentCatalogue(
        populations=TypedDomainRegistry(_items=populations_dict),
        experiments=TypedDomainRegistry(_items=experiments_dict),
        capabilities=tuple(authored_experiments.capabilities),
        suppression_behaviors=tuple(authored_experiments.suppression_behaviors),
        population_readiness_rule=dict(authored_experiments.population_readiness_rule),
        eligibility_gates=TypedDomainRegistry(_items=eligibility_gates_dict),
        analysis_conventions=dict(authored_experiments.analysis_conventions),
    )
