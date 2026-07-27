"""Quantile computation and shared-mean/pooled/weighted/local threshold estimators (B0–B2)."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.numbers import Probability, linear_quantile
from datp_core.thresholding.estimation.models import ThresholdSet, build_threshold_set
from datp_core.thresholding.policies.common import BenignCalibrationScores
from datp_core.thresholding.policies.enums import ThresholdOwnerKind
from datp_core.thresholding.policies.union import (
    SplitConformalThresholdPolicyRecord,
    ThresholdPolicyRecord,
)


def quantile(values: tuple[float, ...], target_quantile: float) -> float:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError("Threshold construction requires finite non-empty calibration scores")
    result = linear_quantile(values, target_quantile)
    if not math.isfinite(result):
        raise ValueError("Threshold construction produced a non-finite quantile")
    return result


def policy_quantile(policy: ThresholdPolicyRecord) -> Probability:
    if isinstance(policy, SplitConformalThresholdPolicyRecord):
        return Probability(policy.nominal_coverage)
    return Probability(policy.quantile)


def estimate_shared_mean(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
) -> ThresholdSet:
    shared = float(np.mean(tuple(local.values())))
    return build_threshold_set(
        policy_id, calibration, dict.fromkeys(local, shared), ThresholdOwnerKind.SHARED_MEAN, target_quantile
    )


def estimate_pooled(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
    quantile_fn: Callable[[tuple[float, ...], float], float],
) -> ThresholdSet:
    pooled = tuple(value for item in calibration for value in item.values)
    threshold = quantile_fn(pooled, target_quantile.value)
    return build_threshold_set(
        policy_id, calibration, {k: threshold for k in local}, ThresholdOwnerKind.POOLED, target_quantile
    )


def estimate_shared_weighted(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
) -> ThresholdSet:
    count = sum(len(item.values) for item in calibration)
    if count == 0:
        raise ValueError("Weighted threshold has no calibration rows")
    threshold = sum(len(item.values) * local[item.client_id.value] for item in calibration) / count
    return build_threshold_set(
        policy_id, calibration, dict.fromkeys(local, threshold), ThresholdOwnerKind.SHARED_WEIGHTED, target_quantile
    )


def estimate_local_quantile(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
) -> ThresholdSet:
    return build_threshold_set(policy_id, calibration, local, ThresholdOwnerKind.LOCAL, target_quantile)
