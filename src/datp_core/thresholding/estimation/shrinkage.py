"""Local-global shrinkage and calibration-fallback threshold estimators."""

from __future__ import annotations

import numpy as np

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.thresholding.estimation.models import ThresholdSet, build_threshold_set
from datp_core.thresholding.policies.common import BenignCalibrationScores
from datp_core.thresholding.policies.enums import ThresholdOwnerKind
from datp_core.thresholding.policies.shrinkage import CalibrationFallbackThresholdPolicyRecord


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
    thresholds = {key: coefficient * value + \
        (1.0 - coefficient) * shared for key, value in local.items()}
    return build_threshold_set(
        policy_id,
        calibration,
        thresholds,
        ThresholdOwnerKind.LOCAL_GLOBAL_SHRINKAGE,
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
    half = policy.weight_formula_constants.n_half
    if half <= 0:
        raise ValueError("Fallback threshold policy requires a positive authored n_half")
    shared = float(np.mean(tuple(local.values())))
    lambdas = {item.client_id.value: len(
        item.values) / (len(item.values) + half) for item in calibration}
    thresholds = {
        item.client_id.value: lambdas[item.client_id.value] * local[item.client_id.value]
        + (1.0 - lambdas[item.client_id.value]) * shared
        for item in calibration
    }
    return build_threshold_set(
        policy_id, calibration, thresholds, ThresholdOwnerKind.CALIBRATION_SHRINKAGE, target_quantile, lambdas
    )
