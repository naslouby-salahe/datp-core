"""Cluster threshold policy record with typed fingerprint, standardization, and KMeans configuration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from attrs import define, field

from datp_core.core.immutability import as_str_mapping
from datp_core.thresholding.policies.common import (
    _as_mapping_str_float_or_mapping,
    _as_tuple_str,
)
from datp_core.thresholding.policies.enums import ClusterAggregation, ThresholdOwnership


@define(frozen=True, slots=True, kw_only=True)
class ClusterFingerprintConfiguration:
    features: tuple[str, ...] = field(converter=_as_tuple_str)
    estimators: Mapping[str, str] = field(converter=as_str_mapping)
    degenerate_client_rules: Mapping[str, float | Mapping[str, float]] = field(
        converter=_as_mapping_str_float_or_mapping
    )
    non_finite_value_behavior: str


@define(frozen=True, slots=True, kw_only=True)
class ClusterStandardizationConfiguration:
    method: str
    with_mean: bool

    @classmethod
    def from_config(cls, config: Mapping[str, str | int]) -> ClusterStandardizationConfiguration:
        return cls(
            method=str(config.get("method", "standard")),
            with_mean=bool(config.get("with_mean", True)),
        )


@define(frozen=True, slots=True, kw_only=True)
class KMeansConfiguration:
    random_seed: int
    initialization_runs: int
    maximum_iterations: int
    convergence_tolerance: float


@define(frozen=True, slots=True, kw_only=True)
class ClusterThresholdPolicyRecord:
    policy: Literal["cluster_threshold"]
    quantile: float
    quantile_estimator: str
    canonical: bool | None
    exploratory: bool | None
    aggregation: ClusterAggregation = field(converter=ClusterAggregation)
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
    required_diagnostics: tuple[str, ...] = field(converter=_as_tuple_str)
    threshold_ownership: ThresholdOwnership = field(converter=ThresholdOwnership)
