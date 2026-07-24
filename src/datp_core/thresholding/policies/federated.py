"""Federated summary-statistic threshold policy records with typed candidate grid and exceedance exchange."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from attrs import define, field

from datp_core.thresholding.policies.common import (
    _as_mapping_str_object,
    _as_tuple_float,
    _as_tuple_str,
)
from datp_core.thresholding.policies.enums import ThresholdOwnership


@define(frozen=True, slots=True, kw_only=True)
class CandidateGrid:
    minimum: float
    maximum: float
    step: float

    @classmethod
    def from_config(cls, config: Mapping[str, str | float | bool]) -> CandidateGrid:
        return cls(
            minimum=float(config["minimum"]),
            maximum=float(config["maximum"]),
            step=float(config["step"]),
        )


@define(frozen=True, slots=True, kw_only=True)
class ExceedanceExchange:
    fields: tuple[str, ...]
    aggregation: str

    @classmethod
    def from_config(cls, config: Mapping[str, tuple[str, ...] | str]) -> ExceedanceExchange:
        raw_fields = config.get("fields", ())
        if isinstance(raw_fields, (list, tuple)):
            return cls(fields=tuple(str(f) for f in raw_fields), aggregation=str(config.get("aggregation", "")))
        return cls(fields=(), aggregation=str(config.get("aggregation", "")))


@define(frozen=True, slots=True, kw_only=True)
class SelectionRules:
    metric: str
    tie_break: str

    @classmethod
    def from_config(cls, config: Mapping[str, str]) -> SelectionRules:
        return cls(
            metric=str(config.get("metric", "")),
            tie_break=str(config.get("tie_break", "")),
        )


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
    candidate_grid: CandidateGrid
    exceedance_exchange: ExceedanceExchange
    selection: SelectionRules
    required_diagnostics: tuple[str, ...] = field(converter=_as_tuple_str)
    threshold_ownership: ThresholdOwnership = field(converter=ThresholdOwnership)


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
    threshold_ownership: ThresholdOwnership = field(converter=ThresholdOwnership)
