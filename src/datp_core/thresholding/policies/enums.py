"""Authoritative threshold-specific closed-domain enums."""

from __future__ import annotations

from enum import StrEnum


class ConformalAttainabilityStatus(StrEnum):
    ATTAINABLE = "attainable"
    UNATTAINABLE = "unattainable"


class ClusterAggregation(StrEnum):
    MEAN = "mean"
    ROBUST_MEDIAN = "robust_median"


class ThresholdOwnership(StrEnum):
    WHOLE_POPULATION = "one_threshold_for_the_whole_eligible_population"
    PER_CLIENT = "one_threshold_per_eligible_client"
    PER_FAMILY = "one_threshold_per_family"
    PER_CLUSTER = "one_threshold_per_cluster"


class ThresholdOwnerKind(StrEnum):
    SHARED_MEAN = "shared_mean"
    POOLED = "pooled"
    SHARED_WEIGHTED = "shared_weighted"
    LOCAL = "local"
    FAMILY_MEAN = "family_mean"
    SPLIT_CONFORMAL = "split_conformal"
    LOCAL_GLOBAL_SHRINKAGE = "local_global_shrinkage"
    CALIBRATION_SHRINKAGE = "calibration_shrinkage"
    FEDERATED_MATCHED_EXCEEDANCE = "federated_matched_exceedance"
    FEDERATED_FIXED_K = "federated_fixed_k"
    CLUSTER = "cluster"


class ThresholdPolicyKind(StrEnum):
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


class CalibrationSelectionStrategy(StrEnum):
    DETERMINISTIC_WITHOUT_REPLACEMENT = "deterministic_without_replacement"


class CalibrationNestingPolicy(StrEnum):
    NESTED_BY_SIZE = "nested_by_size"
