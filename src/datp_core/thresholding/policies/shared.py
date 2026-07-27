"""Shared-mean, pooled, weighted, local-quantile, and centralized-pooled threshold policy records."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from datp_core.thresholding.policies.enums import ThresholdOwnership


class SharedMeanThresholdPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy: Literal["shared_threshold"]
    construction: Literal["mean"]
    quantile: float
    quantile_estimator: str
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: Literal["none"]
    client_accumulation_order: str
    threshold_ownership: ThresholdOwnership


class SharedPooledThresholdPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy: Literal["shared_threshold"]
    construction: Literal["pooled"]
    quantile: float
    quantile_estimator: str
    aggregation_scope: str
    aggregation_formula: str
    concatenation_order: str
    sample_weighting: str
    threshold_ownership: ThresholdOwnership


class SharedWeightedThresholdPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy: Literal["shared_threshold"]
    construction: Literal["weighted"]
    quantile: float
    quantile_estimator: str
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: str
    client_accumulation_order: str
    zero_total_weight_behavior: str
    threshold_ownership: ThresholdOwnership


class LocalQuantileThresholdPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy: Literal["local_threshold"]
    quantile: float
    quantile_estimator: str
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: str
    threshold_ownership: ThresholdOwnership


class CentralizedPooledThresholdPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy: Literal["centralized_pooled_threshold"]
    quantile: float
    quantile_estimator: str
    source_score_population: str
    aggregation_scope: str
    aggregation_formula: str
    concatenation_order: str
    sample_weighting: str
    provenance_separation: str
    threshold_ownership: ThresholdOwnership
