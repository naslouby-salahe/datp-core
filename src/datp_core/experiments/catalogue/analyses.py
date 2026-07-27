"""Analysis specification records — one per AnalysisKind."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum
from typing import cast

from pydantic import BaseModel, ConfigDict, field_validator

from datp_core.core.identifiers import StatisticalProfileId
from datp_core.experiments.catalogue.evaluations import RunRequirement


class AnalysisKind(Enum):
    PAIRED_THRESHOLD = "paired_threshold_analysis"
    ABSORPTION = "absorption_analysis"
    ALERT_BURDEN = "alert_burden_analysis"
    ANCHOR_EQUIVALENCE = "anchor_equivalence_analysis"
    CLUSTER_STABILITY = "cluster_stability_analysis"
    CONFORMAL_COVERAGE = "conformal_coverage_analysis"
    DISTRIBUTION_MECHANISM = "distribution_mechanism_analysis"
    LOCKED_CLIENT_DISTRIBUTION = "locked_client_distribution_analysis"
    METRIC_ASSOCIATION = "metric_association_analysis"
    QUANTILE_ESTIMATION = "quantile_estimation_analysis"
    RECOVERY_FRACTION = "recovery_fraction_analysis"
    RESOURCE_COST = "resource_cost_analysis"
    TEMPORAL_RECOVERY = "temporal_recovery_analysis"
    THRESHOLD_STABILITY = "threshold_stability_analysis"


def _as_reference_analysis(value: object) -> str | Mapping[str, str]:
    if isinstance(value, str):
        return value
    return dict(cast("Iterable[tuple[str, str]]", value))


class PairedThresholdAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    secondary_statistical_profile: StatisticalProfileId | None
    first_evaluation: str
    second_evaluation: str
    primary_metric: str
    delta_orientation: str
    delta_interpretation: str
    required_direction: str | None
    monotonicity_required: bool | None
    ordering_inversion_reporting: str | None
    per_sweep_cell: str | None
    full_curve_reporting: str | bool | None
    post_hoc_weight_selection: str | None


class AbsorptionAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    absorption_metric: str
    formula: str
    band_interpretation: str
    denominator_materiality_rule: float | str
    undefined_denominator_behavior: str
    matching_contract: Mapping[str, object]
    outcome_bands: tuple[Mapping[str, str], ...]
    outcome_bands_are_mutually_exclusive_and_exhaustive: bool
    reference_analysis: str | Mapping[str, str]
    stress_test_analysis: str
    alternative_path_rule: Mapping[str, object] | None

    @field_validator("matching_contract", mode="before")
    @classmethod
    def _convert_matching_contract(cls, v: object) -> Mapping[str, object]:
        return dict(cast("Iterable[tuple[str, object]]", v))

    @field_validator("outcome_bands", mode="before")
    @classmethod
    def _convert_outcome_bands(cls, v: object) -> tuple[Mapping[str, str], ...]:
        if isinstance(v, Iterable):
            return tuple(dict(cast("Iterable[tuple[str, str]]", x)) for x in v)
        raise TypeError(f"Expected iterable for outcome_bands, got {type(v).__name__}")

    @field_validator("reference_analysis", mode="before")
    @classmethod
    def _convert_reference_analysis(cls, v: object) -> str | Mapping[str, str]:
        return _as_reference_analysis(v)

    @field_validator("alternative_path_rule", mode="before")
    @classmethod
    def _convert_alternative_path_rule(cls, v: object) -> Mapping[str, object] | None:
        return dict(cast("Iterable[tuple[str, object]]", v)) if v is not None else None

class AlertBurdenAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    formula: str
    produced_fields: tuple[str, ...]
    source_evaluations: tuple[str, ...]
    required_operational_input: str
    per_client_reporting_required: bool
    unavailable_behavior: str


class AnchorEquivalenceAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_analysis: str
    comparison_mode: str
    comparison_mode_rule: str
    interval_width_tolerance_multiplier: float
    floating_point_tolerance: Mapping[str, float]
    historical_reference: Mapping[str, float | str]
    expected_metric: str
    expected_first_threshold_policy: str
    expected_second_threshold_policy: str
    statistical_fallback_requirements: tuple[str, ...]
    failure_reasons: tuple[str, ...]
    downstream_blocking_behavior: str


class ClusterStabilityAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluation: str
    comparison_unit: str
    produced_fields: tuple[str, ...]
    reference_evaluation: str | None
    run_requirement: RunRequirement | None


class ConformalCoverageAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluation: str
    target_coverage: float
    produced_fields: tuple[str, ...]
    coverage_direction: str | None


class DistributionMechanismAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluations: tuple[str, ...]
    produced_fields: tuple[str, ...]
    field_formulas: Mapping[str, str] | None


class LockedClientDistributionAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluations: tuple[str, ...]
    produced_fields: tuple[str, ...]
    locked_client_identifier: str


class MetricAssociationAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    secondary_statistical_profile: StatisticalProfileId | None
    predictor_metric: str
    outcome_metric: str
    outcome_source_analysis: str
    interpretation_constraint: str
    grouping_dimension: str | None
    calibration_source_evaluation: str | None = None


class QuantileEstimationAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluations: tuple[str, ...]
    produced_fields: tuple[str, ...]
    oracle_reference: str


class RecoveryFractionAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    formula: str
    numerator_analysis: str
    denominator_analysis: str
    denominator_composition: str
    denominator_materiality_rule: float | str
    undefined_denominator_behavior: str


class ResourceCostAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluations: tuple[str, ...]
    produced_fields: tuple[str, ...]
    estimate_basis: str


class TemporalRecoveryAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    primary_metric: str
    static_reference_evaluation: str
    frozen_evaluation: str
    recalibrated_evaluation: str
    recovery_fields: tuple[str, ...]
    drift_excess_formula: str
    recovered_amount_formula: str
    recovery_ratio_formula: str
    meaningful_degradation_rule: str
    recovery_ratio_precondition: str
    negative_recovery_policy: str
    recovery_ratio_direction: str
    meaningful_recovery_threshold: float
    chronology_unverifiable_policy: str
    outcome_bands: tuple[Mapping[str, str], ...]
    outcome_bands_are_mutually_exclusive_and_exhaustive: bool

    @field_validator("outcome_bands", mode="before")
    @classmethod
    def _convert_outcome_bands(cls, v: object) -> tuple[Mapping[str, str], ...]:
        if isinstance(v, Iterable):
            return tuple(dict(cast("Iterable[tuple[str, str]]", x)) for x in v)
        raise TypeError(f"Expected iterable for outcome_bands, got {type(v).__name__}")


class ThresholdStabilityAnalysisRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    kind: str
    result_type: str
    statistical_profile: StatisticalProfileId
    source_evaluation: str
    produced_fields: tuple[str, ...]
    per_sweep_cell: str


AnalysisRecord = (
    PairedThresholdAnalysisRecord
    | AbsorptionAnalysisRecord
    | AlertBurdenAnalysisRecord
    | AnchorEquivalenceAnalysisRecord
    | ClusterStabilityAnalysisRecord
    | ConformalCoverageAnalysisRecord
    | DistributionMechanismAnalysisRecord
    | LockedClientDistributionAnalysisRecord
    | MetricAssociationAnalysisRecord
    | QuantileEstimationAnalysisRecord
    | RecoveryFractionAnalysisRecord
    | ResourceCostAnalysisRecord
    | TemporalRecoveryAnalysisRecord
    | ThresholdStabilityAnalysisRecord
)
