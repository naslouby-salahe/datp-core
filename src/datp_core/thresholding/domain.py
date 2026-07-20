"""Threshold input types prevent attack scores entering calibration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..kernel.ids import ClientId
from ..kernel.values import Probability


class ThresholdPolicyFamily(StrEnum):
    QUANTILE = "quantile"
    CLUSTER = "cluster"
    CONFORMAL = "conformal"
    SHRINKAGE = "shrinkage"
    CALIBRATION_FALLBACK = "calibration_fallback"
    FEDERATED_SUMMARY = "federated_summary"


class ThresholdPolicyId(StrEnum):
    SHARED_MEAN = "shared_mean_p95"
    SHARED_POOLED = "shared_pooled_p95"
    SHARED_WEIGHTED = "shared_weighted_p95"
    LOCAL = "local_p95"
    FAMILY = "family_p95"
    CENTRALIZED = "centralized_pooled_p95"
    CLUSTER_K3_MEAN = "cluster_k3_mean_p95"
    CLUSTER_K9_MEAN = "cluster_k9_mean_p95"
    CLUSTER_K3_MEDIAN = "cluster_k3_robust_median_p95"
    CONFORMAL_LOCAL = "conformal_local_p95"
    SHRINKAGE = "local_global_shrinkage_p95"
    CALIBRATION_FALLBACK = "calibration_size_aware_fallback_p95"
    FEDERATED_MATCHED = "federated_summary_matched_exceedance"
    FEDERATED_FIXED = "federated_summary_fixed_k"


@dataclass(frozen=True, slots=True, kw_only=True)
class BenignCalibrationScores:
    client_id: ClientId
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("benign calibration scores must not be empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdValue:
    client_id: ClientId
    value: float
    owner: str
    calibration_count: int
    fallback_used: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdSet:
    family: ThresholdPolicyFamily
    quantile: Probability
    values: tuple[ThresholdValue, ...]
