"""Federated summary-statistic threshold policy records with typed candidate grid and exceedance exchange."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict

from datp_core.core.immutability import deep_freeze
from datp_core.thresholding.policies.enums import ThresholdOwnership, ThresholdPolicyKind


class CandidateGrid(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class ExceedanceExchange(BaseModel):
    model_config = ConfigDict(frozen=True)

    fields: tuple[str, ...]
    aggregation: str

    @classmethod
    def from_config(cls, config: Mapping[str, tuple[str, ...] | str]) -> ExceedanceExchange:
        raw_fields = config.get("fields", ())
        if isinstance(raw_fields, (list, tuple)):
            return cls(fields=tuple(str(f) for f in raw_fields), aggregation=str(config.get("aggregation", "")))
        return cls(fields=(), aggregation=str(config.get("aggregation", "")))


class SelectionRules(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric: str
    tie_break: str

    @classmethod
    def from_config(cls, config: Mapping[str, str]) -> SelectionRules:
        return cls(
            metric=str(config.get("metric", "")),
            tie_break=str(config.get("tie_break", "")),
        )


class FederatedMatchedExceedanceThresholdPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: ClassVar[ThresholdPolicyKind] = ThresholdPolicyKind.FEDERATED_MATCHED
    policy: Literal["federated_summary_statistic_threshold"]
    mode: Literal["matched_exceedance"]
    quantile: float
    primary_comparator: bool
    client_message: Annotated[Mapping[str, object], BeforeValidator(deep_freeze)]
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
    required_diagnostics: tuple[str, ...]
    threshold_ownership: ThresholdOwnership


class FederatedFixedCoefficientThresholdPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: ClassVar[ThresholdPolicyKind] = ThresholdPolicyKind.FEDERATED_FIXED
    policy: Literal["federated_summary_statistic_threshold"]
    mode: Literal["fixed_k"]
    quantile: float
    primary_comparator: bool
    supplementary_sensitivity_only: bool
    client_message: Annotated[Mapping[str, object], BeforeValidator(deep_freeze)]
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
    fixed_k_grid: tuple[float, ...]
    fixed_k: float | None
    fixed_k_resolution: str
    required_diagnostics: tuple[str, ...]
    threshold_ownership: ThresholdOwnership
