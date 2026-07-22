"""Domain models for threshold policies, benign calibration scores, and estimated threshold sets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, cast

from attrs import define, field

from datp_core.domain.identifiers import ClientId, PopulationId, ThresholdPolicyId
from datp_core.domain.values import NonNegativeFloat, PositiveInt, Probability, deep_freeze


def _as_tuple_str(value: object) -> tuple[str, ...]:
    return cast("tuple[str, ...]", deep_freeze(value))


def _as_tuple_float(value: object) -> tuple[float, ...]:
    return cast("tuple[float, ...]", deep_freeze(value))


def _as_mapping_str_str(value: object) -> Mapping[str, str]:
    return cast("Mapping[str, str]", deep_freeze(value))


def _as_mapping_str_int(value: object) -> Mapping[str, int]:
    return cast("Mapping[str, int]", deep_freeze(value))


def _as_mapping_str_float(value: object) -> Mapping[str, float]:
    return cast("Mapping[str, float]", deep_freeze(value))


def _as_mapping_str_object(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", deep_freeze(value))


def _as_mapping_str_str_or_int(value: object) -> Mapping[str, str | int]:
    return cast("Mapping[str, str | int]", deep_freeze(value))


def _as_mapping_str_str_or_int_or_float(value: object) -> Mapping[str, str | int | float]:
    return cast("Mapping[str, str | int | float]", deep_freeze(value))


def _as_mapping_str_float_or_mapping(value: object) -> Mapping[str, float | Mapping[str, float]]:
    return cast("Mapping[str, float | Mapping[str, float]]", deep_freeze(value))


def _as_mapping_str_str_or_float_or_bool(value: object) -> Mapping[str, str | float | bool]:
    return cast("Mapping[str, str | float | bool]", deep_freeze(value))


def _as_mapping_str_tuple_or_str(value: object) -> Mapping[str, tuple[str, ...] | str]:
    return cast("Mapping[str, tuple[str, ...] | str]", deep_freeze(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class BenignCalibrationScores:
    client_id: ClientId
    values: tuple[float, ...]
    population_id: PopulationId | None = None

    def __post_init__(self) -> None:
        if len(self.values) == 0:
            raise ValueError("Benign calibration score values cannot be empty")
        for val in self.values:
            if not isinstance(val, (int, float)) or val != val or val in (float("inf"), float("-inf")):
                raise ValueError("Calibration score values must be finite numbers")
            if val < 0.0:
                raise ValueError("Calibration anomaly scores must be non-negative")


class ConformalAttainabilityStatus(StrEnum):
    ATTAINABLE = "attainable"
    UNATTAINABLE = "unattainable"


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdRecord:
    client_id: ClientId
    threshold: NonNegativeFloat | float
    owner: str
    effective_lambda: float | None = None
    cluster_label: int | None = None
    finite_sample_rank: int | None = None
    attainability_status: ConformalAttainabilityStatus | None = None

    def __post_init__(self) -> None:
        val = float(self.threshold)
        is_finite = isinstance(val, (int, float)) and val == val and val not in (float("inf"), float("-inf"))
        if not is_finite:
            raise ValueError("Produced threshold value must be finite")
        if val < 0.0:
            raise ValueError("Produced threshold value cannot be negative")
        if self.finite_sample_rank is not None and self.finite_sample_rank < 1:
            raise ValueError("Conformal finite-sample rank must be positive")


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdSet:
    policy_id: ThresholdPolicyId
    values: tuple[ThresholdRecord, ...]
    target_quantile: Probability
    diagnostics: dict[str, object] = field(factory=dict)

    def get_client_threshold(self, client_id: ClientId) -> ThresholdRecord:
        for rec in self.values:
            if rec.client_id == client_id:
                return rec
        raise KeyError(f"No threshold record for client: {client_id}")


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleSizeCheck:
    client_id: ClientId
    calibration_count: PositiveInt | int
    minimum_required: PositiveInt | int

    @property
    def is_sufficient(self) -> bool:
        return int(self.calibration_count) >= int(self.minimum_required)


@define(frozen=True, slots=True, kw_only=True)
class SharedMeanThresholdPolicyRecord:
    policy: Literal["shared_threshold"]
    construction: Literal["mean"]
    quantile: float
    quantile_estimator: str
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: Literal["none"]
    client_accumulation_order: str
    threshold_ownership: str


@define(frozen=True, slots=True, kw_only=True)
class SharedPooledThresholdPolicyRecord:
    policy: Literal["shared_threshold"]
    construction: Literal["pooled"]
    quantile: float
    quantile_estimator: str
    aggregation_scope: str
    aggregation_formula: str
    concatenation_order: str
    sample_weighting: str
    threshold_ownership: str


@define(frozen=True, slots=True, kw_only=True)
class SharedWeightedThresholdPolicyRecord:
    policy: Literal["shared_threshold"]
    construction: Literal["weighted"]
    quantile: float
    quantile_estimator: str
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: str
    client_accumulation_order: str
    zero_total_weight_behavior: str
    threshold_ownership: str


@define(frozen=True, slots=True, kw_only=True)
class LocalQuantileThresholdPolicyRecord:
    policy: Literal["local_threshold"]
    quantile: float
    quantile_estimator: str
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: str
    threshold_ownership: str


@define(frozen=True, slots=True, kw_only=True)
class FamilyMeanThresholdPolicyRecord:
    policy: Literal["family_threshold"]
    quantile: float
    quantile_estimator: str
    requires_capability: str
    taxonomy_source: str
    aggregated_quantity: str
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: str
    client_accumulation_order: str
    singleton_family_behavior: str
    family_with_no_eligible_member_behavior: str
    client_without_family_label_behavior: str
    unavailable_without_taxonomy: str
    threshold_ownership: str


@define(frozen=True, slots=True, kw_only=True)
class CentralizedPooledThresholdPolicyRecord:
    policy: Literal["centralized_pooled_threshold"]
    quantile: float
    quantile_estimator: str
    source_score_population: str
    aggregation_scope: str
    aggregation_formula: str
    concatenation_order: str
    sample_weighting: str
    provenance_separation: str
    threshold_ownership: str


@define(frozen=True, slots=True, kw_only=True)
class ClusterThresholdPolicyRecord:
    policy: Literal["cluster_threshold"]
    quantile: float
    quantile_estimator: str
    canonical: bool | None
    exploratory: bool | None
    aggregation: str
    cluster_count: int
    aggregated_quantity: str
    aggregation_formula: str
    median_estimator: str | None
    sample_weighting: str
    client_accumulation_order: str
    fingerprint_features: tuple[str, ...] = field(converter=_as_tuple_str)
    fingerprint_estimators: Mapping[str, str] = field(converter=_as_mapping_str_str)
    fingerprint_degenerate_client_rules: Mapping[str, float | Mapping[str, float]] = field(
        converter=_as_mapping_str_float_or_mapping
    )
    fingerprint_non_finite_value_behavior: str
    standardization: Mapping[str, str | int] = field(converter=_as_mapping_str_str_or_int)
    client_ordering_before_fit: str
    clustering: Mapping[str, str | int | float] = field(converter=_as_mapping_str_str_or_int_or_float)
    label_canonicalization: str
    insufficient_eligible_clients_behavior: str
    degenerate_fingerprint_matrix_behavior: str
    required_diagnostics: tuple[str, ...] = field(converter=_as_tuple_str)
    threshold_ownership: str


@define(frozen=True, slots=True, kw_only=True)
class SplitConformalThresholdPolicyRecord:
    policy: Literal["conformal_local_threshold"]
    conformal_mode: str
    coverage_alpha: float
    nominal_coverage: float
    target_exceedance: float
    rank_formula: str
    order_statistic_selection: str
    interpolation: str
    tie_break: str
    finite_sample_attainability_rule: str
    unattainable_behavior: str
    minimum_sample_count: int
    calibration_unit: str
    calibration_scope: str
    evaluation_unit: str
    coverage_breakdown: tuple[str, ...] = field(converter=_as_tuple_str)
    coverage_target_error: str
    output_type: str
    exchangeability_limitation: str
    unavailable_behavior: str
    threshold_ownership: str


@define(frozen=True, slots=True, kw_only=True)
class LocalGlobalShrinkageThresholdPolicyRecord:
    policy: Literal["local_global_shrinkage_threshold"]
    quantile: float
    quantile_estimator: str
    local_reference: str
    global_reference: str
    interpolation_formula: str
    weight_semantics: str
    weight_scope: str
    permitted_weight_range: Mapping[str, float] = field(converter=_as_mapping_str_float)
    shrinkage_weight_grid: tuple[float, ...] = field(converter=_as_tuple_float)
    shrinkage_weight: float | None
    shrinkage_weight_resolution: str
    out_of_range_weight_behavior: str
    effective_lambda_reporting: str
    threshold_ownership: str


@define(frozen=True, slots=True, kw_only=True)
class CalibrationFallbackThresholdPolicyRecord:
    policy: Literal["calibration_size_aware_fallback_threshold"]
    quantile: float
    quantile_estimator: str
    local_reference: str
    global_reference: str
    interpolation_formula: str
    weight_semantics: str
    weight_scope: str
    weight_formula: str
    weight_formula_constants: Mapping[str, int] = field(converter=_as_mapping_str_int)
    weight_monotone_in_calibration_count: bool
    clamping: str
    permitted_weight_range: Mapping[str, float] = field(converter=_as_mapping_str_float)
    zero_calibration_behavior: str
    minimum_calibration_behavior: str
    effective_lambda_reporting: str
    fallback_frequency_reporting: str
    threshold_ownership: str


@define(frozen=True, slots=True, kw_only=True)
class FederatedMatchedExceedanceThresholdPolicyRecord:
    policy: Literal["federated_summary_statistic_threshold"]
    mode: Literal["matched_exceedance"]
    quantile: float
    primary_comparator: bool
    client_message: Mapping[str, object] = field(converter=_as_mapping_str_object)
    global_mean_formula: str
    within_term_formula: str
    between_term_formula: str
    pooled_variance_formula: str
    between_term_mandatory: bool
    between_ratio_formula: str
    between_ratio_zero_denominator_behavior: str
    global_standard_deviation_formula: str
    client_accumulation_order: str
    zero_total_count_behavior: str
    candidate_grid: Mapping[str, str | float | bool] = field(converter=_as_mapping_str_str_or_float_or_bool)
    exceedance_exchange: Mapping[str, tuple[str, ...] | str] = field(converter=_as_mapping_str_tuple_or_str)
    selection: Mapping[str, str] = field(converter=_as_mapping_str_str)
    required_diagnostics: tuple[str, ...] = field(converter=_as_tuple_str)
    threshold_ownership: str


@define(frozen=True, slots=True, kw_only=True)
class FederatedFixedCoefficientThresholdPolicyRecord:
    policy: Literal["federated_summary_statistic_threshold"]
    mode: Literal["fixed_k"]
    quantile: float
    primary_comparator: bool
    supplementary_sensitivity_only: bool
    client_message: Mapping[str, object] = field(converter=_as_mapping_str_object)
    global_mean_formula: str
    within_term_formula: str
    between_term_formula: str
    pooled_variance_formula: str
    between_term_mandatory: bool
    between_ratio_formula: str
    between_ratio_zero_denominator_behavior: str
    global_standard_deviation_formula: str
    client_accumulation_order: str
    zero_total_count_behavior: str
    threshold_formula: str
    fixed_k_grid: tuple[float, ...] = field(converter=_as_tuple_float)
    fixed_k: float | None
    fixed_k_resolution: str
    required_diagnostics: tuple[str, ...] = field(converter=_as_tuple_str)
    threshold_ownership: str


ThresholdPolicyRecord = (
    SharedMeanThresholdPolicyRecord
    | SharedPooledThresholdPolicyRecord
    | SharedWeightedThresholdPolicyRecord
    | LocalQuantileThresholdPolicyRecord
    | FamilyMeanThresholdPolicyRecord
    | CentralizedPooledThresholdPolicyRecord
    | ClusterThresholdPolicyRecord
    | SplitConformalThresholdPolicyRecord
    | LocalGlobalShrinkageThresholdPolicyRecord
    | CalibrationFallbackThresholdPolicyRecord
    | FederatedMatchedExceedanceThresholdPolicyRecord
    | FederatedFixedCoefficientThresholdPolicyRecord
)
