"""Local-global shrinkage and calibration-size-aware-fallback (combination-over-existing-thresholds
policies), plus the federated summary-statistic (B-FedStatsBenign) matched-exceedance/fixed-k
threshold families. Combined into one file because both are "combine already-computed local/shared
thresholds" policies sharing pooled-moment math, per TARGET_ARCHITECTURE.md deviation #3.
"""

from __future__ import annotations

import math

import numpy as np

from datp_core.thresholding.models import (
    BenignCalibrationScores,
    CalibrationFallbackThresholdPolicyRecord,
    FederatedMatchedExceedanceThresholdPolicyRecord,
    Probability,
    ThresholdPolicyId,
    ThresholdSet,
    build_threshold_set,
)


def estimate_shrinkage(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
    coefficient: float,
) -> ThresholdSet:
    if not 0.0 <= coefficient <= 1.0:
        raise ValueError("Shrinkage coefficient is outside the authored permitted range")
    shared = float(np.mean(tuple(local.values())))
    thresholds = {key: coefficient * value + (1.0 - coefficient) * shared for key, value in local.items()}
    return build_threshold_set(
        policy_id,
        calibration,
        thresholds,
        "local_global_shrinkage",
        target_quantile,
        dict.fromkeys(local, coefficient),
    )


def estimate_calibration_fallback(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    local: dict[str, float],
    target_quantile: Probability,
    policy: CalibrationFallbackThresholdPolicyRecord,
) -> ThresholdSet:
    half = policy.weight_formula_constants.get("n_half")
    if not isinstance(half, int) or half <= 0:
        raise ValueError("Fallback threshold policy requires a positive authored n_half")
    shared = float(np.mean(tuple(local.values())))
    lambdas = {item.client_id.value: len(item.values) / (len(item.values) + half) for item in calibration}
    thresholds = {
        item.client_id.value: lambdas[item.client_id.value] * local[item.client_id.value]
        + (1.0 - lambdas[item.client_id.value]) * shared
        for item in calibration
    }
    return build_threshold_set(
        policy_id, calibration, thresholds, "calibration_shrinkage", target_quantile, lambdas
    )


def federated_moments(calibration: tuple[BenignCalibrationScores, ...]) -> tuple[float, float]:
    counts = np.asarray([len(item.values) for item in calibration], dtype=np.float64)
    means = np.asarray([np.mean(item.values) for item in calibration], dtype=np.float64)
    variances = np.asarray([np.var(item.values) for item in calibration], dtype=np.float64)
    total = float(np.sum(counts))
    if total <= 0.0:
        raise ValueError("Federated summary threshold has no calibration rows")
    mean = float(np.sum(counts * means) / total)
    variance = float(np.sum(counts * variances) / total + np.sum(counts * (means - mean) ** 2) / total)
    return mean, math.sqrt(variance)


def estimate_federated_matched(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    policy: FederatedMatchedExceedanceThresholdPolicyRecord,
) -> ThresholdSet:
    minimum = policy.candidate_grid.get("minimum")
    maximum = policy.candidate_grid.get("maximum")
    step = policy.candidate_grid.get("step")
    if not isinstance(minimum, float) or not isinstance(maximum, float) or not isinstance(step, float):
        raise ValueError("Matched-exceedance policy has an invalid authored candidate grid")
    if step <= 0.0:
        raise ValueError("Matched-exceedance policy has an invalid authored candidate grid")
    mean, standard_deviation = federated_moments(calibration)
    candidates = np.arange(minimum, maximum + step / 2.0, step)
    scores = np.asarray([score for item in calibration for score in item.values], dtype=np.float64)
    achieved = np.asarray([np.mean(scores > mean + candidate * standard_deviation) for candidate in candidates])
    deviation = np.abs(achieved - (1.0 - target_quantile.value))
    winner = candidates[np.flatnonzero(deviation == np.min(deviation))[-1]]
    threshold = mean + float(winner) * standard_deviation
    diagnostics: dict[str, object] = {
        "selected_coefficient": float(winner),
        "candidate_grid": {"minimum": minimum, "maximum": maximum, "step": step},
        "pooled_mean": float(mean),
        "pooled_standard_deviation": float(standard_deviation),
        "achieved_exceedance": {float(c): float(a) for c, a in zip(candidates, achieved, strict=True)},
        "tie_set": [float(candidates[i]) for i in np.flatnonzero(deviation == np.min(deviation))],
    }
    return build_threshold_set(
        policy_id,
        calibration,
        {item.client_id.value: threshold for item in calibration},
        "federated_matched_exceedance",
        target_quantile,
        diagnostics=diagnostics,
    )


def estimate_federated_fixed(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    coefficient: float,
) -> ThresholdSet:
    mean, standard_deviation = federated_moments(calibration)
    threshold = mean + coefficient * standard_deviation
    return build_threshold_set(
        policy_id,
        calibration,
        {item.client_id.value: threshold for item in calibration},
        "federated_fixed_k",
        target_quantile,
    )
