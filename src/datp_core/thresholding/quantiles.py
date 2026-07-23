"""Shared-mean/pooled/weighted, local-quantile, and family-mean threshold estimation (B0-B3)."""

from __future__ import annotations

import numpy as np

from datp_core.thresholding.models import (
    BenignCalibrationScores,
    Probability,
    ThresholdPolicyId,
    ThresholdSet,
    build_threshold_set,
)


def estimate_shared_mean(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
) -> ThresholdSet:
    shared = float(np.mean(tuple(local.values())))
    return build_threshold_set(policy_id, calibration, dict.fromkeys(local, shared), "shared_mean", target_quantile)


def estimate_pooled(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
    quantile_fn,
) -> ThresholdSet:
    """Shared for `SharedPooledThresholdPolicyRecord` and `CentralizedPooledThresholdPolicyRecord`."""
    pooled = tuple(value for item in calibration for value in item.values)
    threshold = quantile_fn(pooled, target_quantile.value)
    return build_threshold_set(policy_id, calibration, dict.fromkeys(local, threshold), "pooled", target_quantile)


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
        policy_id, calibration, dict.fromkeys(local, threshold), "shared_weighted", target_quantile
    )


def estimate_local_quantile(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
) -> ThresholdSet:
    return build_threshold_set(policy_id, calibration, local, "local", target_quantile)


def estimate_family_mean(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
    family_map: dict[str, str] | None,
) -> ThresholdSet:
    if family_map is None:
        raise ValueError("Family threshold requires an explicit resolved client-family mapping")
    families: dict[str, list[float]] = {}
    for item in calibration:
        family = family_map.get(item.client_id.value)
        if family is None:
            raise ValueError(f"Client '{item.client_id.value}' has no configured family")
        families.setdefault(family, []).append(local[item.client_id.value])
    family_thresholds = {family: float(np.mean(values)) for family, values in families.items()}
    thresholds = {
        item.client_id.value: family_thresholds[family_map[item.client_id.value]] for item in calibration
    }
    return build_threshold_set(policy_id, calibration, thresholds, "family_mean", target_quantile)
