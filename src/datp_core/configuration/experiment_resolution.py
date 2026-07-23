"""Experiment-resolution functions extracted from the monolithic resolver.

Ownership boundary: converts authored experiment Pydantic models into immutable
domain records owned by ``experiments/models.py``. Exports a narrow function surface;
does not import pipeline execution, CLI, or infrastructure.
"""

from __future__ import annotations

from typing import cast


from datp_core.configuration.fingerprints import unstructure_projection
from datp_core.configuration.loading import ConfigurationError
from datp_core.configuration.models import AnalysisSpecConfig, AuthoredExperimentConfig, SweepVariableConfig
from datp_core.experiments.models import (
    AbsorptionAnalysisRecord,
    AlertBurdenAnalysisRecord,
    AnalysisRecord,
    AnchorEquivalenceAnalysisRecord,
    ClusterStabilityAnalysisRecord,
    ConditionSweepRecord,
    ConformalCoverageAnalysisRecord,
    DistributionMechanismAnalysisRecord,
    ExperimentRecord,
    LockedClientDistributionAnalysisRecord,
    MetricAssociationAnalysisRecord,
    PairedThresholdAnalysisRecord,
    QuantileEstimationAnalysisRecord,
    RecoveryFractionAnalysisRecord,
    ResourceCostAnalysisRecord,
    RunRequirement,
    SweepConditionRecord,
    SweepRecord,
    SweepValue,
    TemporalRecoveryAnalysisRecord,
    ThresholdStabilityAnalysisRecord,
    ValueSweepRecord,
)
from datp_core.pipeline.identifiers import (
    StatisticalProfileId,
)


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
            SweepConditionRecord(name=c.name, allocation=c.allocation, dirichlet_alpha=c.dirichlet_alpha)
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
        first_evaluation=cast(str, _require(getattr(a, "first_evaluation"), experiment_name=exp_name, analysis_label=a.label, field_name="first_evaluation")),
        second_evaluation=cast(str, _require(getattr(a, "second_evaluation"), experiment_name=exp_name, analysis_label=a.label, field_name="second_evaluation")),
        primary_metric=cast(str, _require(getattr(a, "primary_metric"), experiment_name=exp_name, analysis_label=a.label, field_name="primary_metric")),
        delta_orientation=cast(str, _require(getattr(a, "delta_orientation"), experiment_name=exp_name, analysis_label=a.label, field_name="delta_orientation")),
        delta_interpretation=cast(str, _require(getattr(a, "delta_interpretation"), experiment_name=exp_name, analysis_label=a.label, field_name="delta_interpretation")),
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
        primary_metric=cast(str, _require(getattr(a, "primary_metric"), experiment_name=exp_name, analysis_label=a.label, field_name="primary_metric")),
        static_reference_evaluation=cast(str, _require(getattr(a, "static_reference_evaluation"), experiment_name=exp_name, analysis_label=a.label, field_name="static_reference_evaluation")),
        frozen_evaluation=cast(str, _require(getattr(a, "frozen_evaluation"), experiment_name=exp_name, analysis_label=a.label, field_name="frozen_evaluation")),
        recalibrated_evaluation=cast(str, _require(getattr(a, "recalibrated_evaluation"), experiment_name=exp_name, analysis_label=a.label, field_name="recalibrated_evaluation")),
        recovery_fields=_tuple_str_list(_require(getattr(a, "recovery_fields"), experiment_name=exp_name, analysis_label=a.label, field_name="recovery_fields")),
        drift_excess_formula=cast(str, _require(getattr(a, "drift_excess_formula"), experiment_name=exp_name, analysis_label=a.label, field_name="drift_excess_formula")),
        recovered_amount_formula=cast(str, _require(getattr(a, "recovered_amount_formula"), experiment_name=exp_name, analysis_label=a.label, field_name="recovered_amount_formula")),
        recovery_ratio_formula=cast(str, _require(getattr(a, "recovery_ratio_formula"), experiment_name=exp_name, analysis_label=a.label, field_name="recovery_ratio_formula")),
        meaningful_degradation_rule=cast(str, _require(getattr(a, "meaningful_degradation_rule"), experiment_name=exp_name, analysis_label=a.label, field_name="meaningful_degradation_rule")),
        recovery_ratio_precondition=cast(str, _require(getattr(a, "recovery_ratio_precondition"), experiment_name=exp_name, analysis_label=a.label, field_name="recovery_ratio_precondition")),
        negative_recovery_policy=cast(str, _require(getattr(a, "negative_recovery_policy"), experiment_name=exp_name, analysis_label=a.label, field_name="negative_recovery_policy")),
        recovery_ratio_direction=cast(str, _require(getattr(a, "recovery_ratio_direction"), experiment_name=exp_name, analysis_label=a.label, field_name="recovery_ratio_direction")),
        chronology_unverifiable_policy=cast(str, _require(getattr(a, "chronology_unverifiable_policy"), experiment_name=exp_name, analysis_label=a.label, field_name="chronology_unverifiable_policy")),
        outcome_bands=cast(list, _require(getattr(a, "outcome_bands"), experiment_name=exp_name, analysis_label=a.label, field_name="outcome_bands")),
        outcome_bands_are_mutually_exclusive_and_exhaustive=cast(
            bool, _require(getattr(a, "outcome_bands_are_mutually_exclusive_and_exhaustive"), experiment_name=exp_name, analysis_label=a.label, field_name="outcome_bands_are_mutually_exclusive_and_exhaustive")
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

    if a.kind == "paired_threshold_analysis":
        return _build_paired_threshold_analysis_record(exp_cfg.name, a, statistical_profile, secondary_statistical_profile)
    if a.kind == "absorption_analysis":
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
    if a.kind == "alert_burden_analysis":
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
    if a.kind == "anchor_equivalence_analysis":
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
    if a.kind == "cluster_stability_analysis":
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
    if a.kind == "conformal_coverage_analysis":
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
    if a.kind == "distribution_mechanism_analysis":
        return DistributionMechanismAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluations=_tuple_str_list(req("source_evaluations")),
            produced_fields=_tuple_str_list(req("produced_fields")),
            field_formulas=a.field_formulas,
        )
    if a.kind == "locked_client_distribution_analysis":
        return LockedClientDistributionAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluations=_tuple_str_list(req("source_evaluations")),
            produced_fields=_tuple_str_list(req("produced_fields")),
            locked_client_identifier=cast(str, req("locked_client_identifier")),
        )
    if a.kind == "metric_association_analysis":
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
    if a.kind == "quantile_estimation_analysis":
        return QuantileEstimationAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluations=_tuple_str_list(req("source_evaluations")),
            produced_fields=_tuple_str_list(req("produced_fields")),
            oracle_reference=cast(str, req("oracle_reference")),
        )
    if a.kind == "recovery_fraction_analysis":
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
    if a.kind == "resource_cost_analysis":
        return ResourceCostAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluations=_tuple_str_list(req("source_evaluations")),
            produced_fields=_tuple_str_list(req("produced_fields")),
            estimate_basis=cast(str, req("estimate_basis")),
        )
    if a.kind == "temporal_recovery_analysis":
        return _build_temporal_recovery_analysis_record(exp_cfg.name, a, statistical_profile)
    if a.kind == "threshold_stability_analysis":
        return ThresholdStabilityAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluation=cast(str, req("source_evaluation")),
            produced_fields=_tuple_str_list(req("produced_fields")),
            per_sweep_cell=cast(str, req("per_sweep_cell")),
        )
    raise ConfigurationError(f"Experiment '{exp_cfg.name}' analysis '{a.label}' has unsupported kind '{a.kind}'")
