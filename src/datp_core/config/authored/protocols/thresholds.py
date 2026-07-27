"""Authored threshold policy contracts: the closed threshold-policy discriminated union."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from datp_core.config.authored.base import StrictFrozenConfigModel


class BaseThresholdPolicyConfig(StrictFrozenConfigModel):
    quantile: float = Field(ge=0.0, le=1.0)


class SharedMeanThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["shared_threshold"]
    construction: Literal["mean"]
    threshold_ownership: str


class SharedPooledThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["shared_threshold"]
    construction: Literal["pooled"]
    threshold_ownership: str


class SharedWeightedThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["shared_threshold"]
    construction: Literal["weighted"]
    threshold_ownership: str


class LocalQuantileThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["local_threshold"]
    threshold_ownership: str


class FamilyMeanThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["family_threshold"]
    threshold_ownership: str


class CentralizedPooledThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["centralized_pooled_threshold"]
    threshold_ownership: str


class ClusterThresholdPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["cluster_threshold"]
    aggregation: str
    cluster_count: int = Field(ge=1)
    fingerprint_features: list[str]
    fingerprint_quantile: float
    clustering: dict[str, str | int | float]
    threshold_ownership: str


class SplitConformalThresholdPolicyConfig(StrictFrozenConfigModel):
    policy: Literal["conformal_local_threshold"]
    coverage_alpha: float
    nominal_coverage: float
    target_exceedance: float
    minimum_sample_count: int
    threshold_ownership: str


class LocalGlobalShrinkagePolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["local_global_shrinkage_threshold"]
    shrinkage_weight_grid: list[float]
    shrinkage_weight: float | None = None
    threshold_ownership: str


class CalibrationFallbackPolicyConfig(BaseThresholdPolicyConfig):
    policy: Literal["calibration_size_aware_fallback_threshold"]
    n_half: int
    threshold_ownership: str


class FederatedMatchedExceedancePolicyConfig(StrictFrozenConfigModel):
    policy: Literal["federated_summary_statistic_threshold"]
    mode: Literal["matched_exceedance"]
    quantile: float = Field(ge=0.0, le=1.0)
    candidate_grid: dict[str, str | float | bool]
    threshold_ownership: str


class FederatedFixedCoefficientPolicyConfig(StrictFrozenConfigModel):
    policy: Literal["federated_summary_statistic_threshold"]
    mode: Literal["fixed_k"]
    quantile: float = Field(ge=0.0, le=1.0)
    fixed_k_grid: list[float]
    fixed_k: float | None = None
    threshold_ownership: str


TypedThresholdPolicyConfig = (
    SharedMeanThresholdPolicyConfig
    | SharedPooledThresholdPolicyConfig
    | SharedWeightedThresholdPolicyConfig
    | LocalQuantileThresholdPolicyConfig
    | FamilyMeanThresholdPolicyConfig
    | CentralizedPooledThresholdPolicyConfig
    | ClusterThresholdPolicyConfig
    | SplitConformalThresholdPolicyConfig
    | LocalGlobalShrinkagePolicyConfig
    | CalibrationFallbackPolicyConfig
    | FederatedMatchedExceedancePolicyConfig
    | FederatedFixedCoefficientPolicyConfig
)
