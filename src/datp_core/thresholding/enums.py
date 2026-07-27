"""Authoritative thresholding closed-domain enums."""

from __future__ import annotations

from enum import StrEnum


class ThresholdDiagnosticsKind(StrEnum):
    """Every implemented threshold diagnostics variant."""

    CLUSTER = "cluster"
    CONFORMAL = "conformal"
    SHRINKAGE = "shrinkage"
    CALIBRATION_FALLBACK = "calibration_fallback"
    FEDERATED_MATCHED = "federated_matched"
    FEDERATED_FIXED = "federated_fixed"


class ThresholdPolicyKind(StrEnum):
    """Every implemented threshold construction strategy."""

    SHARED_MEAN = "shared_mean"
    SHARED_POOLED = "shared_pooled"
    SHARED_WEIGHTED = "shared_weighted"
    LOCAL_QUANTILE = "local_quantile"
    FAMILY_MEAN = "family_mean"
    CLUSTER = "cluster"
    CONFORMAL = "conformal"
    SHRINKAGE = "shrinkage"
    CALIBRATION_FALLBACK = "calibration_fallback"
    FEDERATED_MATCHED = "federated_matched"
    FEDERATED_FIXED = "federated_fixed"


class ThresholdScope(StrEnum):
    """Output granularity of constructed thresholds."""

    SHARED = "shared"
    CLIENT = "client"
    FAMILY = "family"
    CLUSTER = "cluster"


class ClusterAggregation(StrEnum):
    MEAN = "mean"
    ROBUST_MEDIAN = "robust_median"


class FingerprintFeature(StrEnum):
    MEAN_ERROR = "mean_error"
    STD_ERROR = "std_error"
    SKEW_ERROR = "skew_error"
    QUANTILE_ERROR = "quantile_error"


class TieBreakRule(StrEnum):
    SELECT_HIGHEST_COEFFICIENT = "select_highest_coefficient"
