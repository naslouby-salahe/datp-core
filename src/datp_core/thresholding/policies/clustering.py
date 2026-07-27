"""Cluster threshold policy record with typed fingerprint, standardization, and KMeans configuration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict

from datp_core.core.immutability import as_str_mapping
from datp_core.thresholding.policies.common import (
    _as_mapping_str_float_or_mapping,
    _as_tuple_str,
)
from datp_core.thresholding.policies.enums import ClusterAggregation, ThresholdOwnership


class ClusterFingerprintConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True)

    features: Annotated[tuple[str, ...], BeforeValidator(_as_tuple_str)]
    estimators: Annotated[Mapping[str, str], BeforeValidator(as_str_mapping)]
    degenerate_client_rules: Annotated[
        Mapping[str, float | Mapping[str, float]], BeforeValidator(_as_mapping_str_float_or_mapping)
    ]
    non_finite_value_behavior: str


class ClusterStandardizationConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: str
    with_mean: bool

    @classmethod
    def from_config(cls, config: Mapping[str, str | int]) -> ClusterStandardizationConfiguration:
        return cls(
            method=str(config.get("method", "standard")),
            with_mean=bool(config.get("with_mean", True)),
        )


class KMeansConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True)

    random_seed: int
    initialization_runs: int
    maximum_iterations: int
    convergence_tolerance: float


class ClusterThresholdPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy: Literal["cluster_threshold"]
    quantile: float
    quantile_estimator: str
    canonical: bool | None
    exploratory: bool | None
    aggregation: ClusterAggregation
    cluster_count: int
    aggregated_quantity: str
    aggregation_formula: str
    median_estimator: str | None
    sample_weighting: str
    client_accumulation_order: str
    fingerprint: ClusterFingerprintConfiguration
    standardization: ClusterStandardizationConfiguration
    client_ordering_before_fit: str
    kmeans: KMeansConfiguration
    label_canonicalization: str
    insufficient_eligible_clients_behavior: str
    degenerate_fingerprint_matrix_behavior: str
    required_diagnostics: Annotated[tuple[str, ...], BeforeValidator(_as_tuple_str)]
    threshold_ownership: ThresholdOwnership
