"""Authored per-experiment analysis specifications as a closed discriminated union.

Each analysis kind gets its own model requiring exactly the fields that analysis needs and
omitting fields that belong to other analyses -- replacing the single mostly-optional superset
model and the resolver `_require()`/`cast()` calls that existed only to cover for it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from datp_core.config.authored.base import StrictFrozenConfigModel


class MatchingContractConfig(StrictFrozenConfigModel):
    required_equal: list[str]
    permitted_to_differ: list[str] | None = None
    evaluation_label_mapping: dict[str, dict[str, str]] | None = None


class AlternativePathRuleConfig(StrictFrozenConfigModel):
    formula: str
    reported_independently_of_the_absorption_band: bool


class _AnalysisSpecBase(StrictFrozenConfigModel):
    label: str
    result_type: str
    statistical_profile: str


class PairedThresholdAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["paired_threshold_analysis"]
    first_evaluation: str
    second_evaluation: str
    primary_metric: str
    delta_orientation: str
    delta_interpretation: str
    secondary_statistical_profile: str | None = None
    required_direction: str | None = None
    monotonicity_required: bool | None = None
    ordering_inversion_reporting: str | None = None
    per_sweep_cell: str | None = None
    full_curve_reporting: str | bool | None = None
    post_hoc_weight_selection: str | None = None


class AbsorptionAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["absorption_analysis"]
    absorption_metric: str
    formula: str
    band_interpretation: str
    denominator_materiality_rule: float | str
    undefined_denominator_behavior: str
    matching_contract: MatchingContractConfig
    outcome_bands: list[dict[str, str]]
    outcome_bands_are_mutually_exclusive_and_exhaustive: bool
    reference_analysis: str | dict[str, str]
    stress_test_analysis: str
    alternative_path_rule: AlternativePathRuleConfig | None = None


class AlertBurdenAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["alert_burden_analysis"]
    formula: str
    produced_fields: list[str]
    source_evaluations: list[str]
    required_operational_input: str
    per_client_reporting_required: bool
    unavailable_behavior: str


class AnchorEquivalenceAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["anchor_equivalence_analysis"]
    source_analysis: str
    comparison_mode: str
    comparison_mode_rule: str
    interval_width_tolerance_multiplier: float
    floating_point_tolerance: dict[str, float]
    historical_reference: dict[str, float | str]
    expected_metric: str
    expected_first_threshold_policy: str
    expected_second_threshold_policy: str
    statistical_fallback_requirements: list[str]
    failure_reasons: list[str]
    downstream_blocking_behavior: str


class ClusterStabilityAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["cluster_stability_analysis"]
    source_evaluation: str
    comparison_unit: str
    produced_fields: list[str]
    reference_evaluation: str | None = None
    run_requirement: str | None = None


class ConformalCoverageAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["conformal_coverage_analysis"]
    source_evaluation: str
    target_coverage: float
    produced_fields: list[str]
    coverage_direction: str | None = None


class DistributionMechanismAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["distribution_mechanism_analysis"]
    source_evaluations: list[str]
    produced_fields: list[str]
    field_formulas: dict[str, str] | None = None


class LockedClientDistributionAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["locked_client_distribution_analysis"]
    source_evaluations: list[str]
    produced_fields: list[str]
    locked_client_identifier: str


class MetricAssociationAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["metric_association_analysis"]
    predictor_metric: str
    outcome_metric: str
    outcome_source_analysis: str
    interpretation_constraint: str
    secondary_statistical_profile: str | None = None
    grouping_dimension: str | None = None


class QuantileEstimationAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["quantile_estimation_analysis"]
    source_evaluations: list[str]
    produced_fields: list[str]
    oracle_reference: str


class RecoveryFractionAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["recovery_fraction_analysis"]
    formula: str
    numerator_analysis: str
    denominator_analysis: str
    denominator_composition: str
    denominator_materiality_rule: float | str
    undefined_denominator_behavior: str


class ResourceCostAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["resource_cost_analysis"]
    source_evaluations: list[str]
    produced_fields: list[str]
    estimate_basis: str


class TemporalRecoveryAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["temporal_recovery_analysis"]
    primary_metric: str
    static_reference_evaluation: str
    frozen_evaluation: str
    recalibrated_evaluation: str
    recovery_fields: list[str]
    drift_excess_formula: str
    recovered_amount_formula: str
    recovery_ratio_formula: str
    meaningful_degradation_rule: str
    recovery_ratio_precondition: str
    negative_recovery_policy: str
    recovery_ratio_direction: str
    meaningful_recovery_threshold: float
    chronology_unverifiable_policy: str
    outcome_bands: list[dict[str, str]]
    outcome_bands_are_mutually_exclusive_and_exhaustive: bool


class ThresholdStabilityAnalysisConfig(_AnalysisSpecBase):
    kind: Literal["threshold_stability_analysis"]
    source_evaluation: str
    produced_fields: list[str]
    per_sweep_cell: str


AnalysisSpecConfig = (
    PairedThresholdAnalysisConfig
    | AbsorptionAnalysisConfig
    | AlertBurdenAnalysisConfig
    | AnchorEquivalenceAnalysisConfig
    | ClusterStabilityAnalysisConfig
    | ConformalCoverageAnalysisConfig
    | DistributionMechanismAnalysisConfig
    | LockedClientDistributionAnalysisConfig
    | MetricAssociationAnalysisConfig
    | QuantileEstimationAnalysisConfig
    | RecoveryFractionAnalysisConfig
    | ResourceCostAnalysisConfig
    | TemporalRecoveryAnalysisConfig
    | ThresholdStabilityAnalysisConfig
)
TypedAnalysisSpecConfig = Field(discriminator="kind")
