"""Federated summary-statistic threshold estimators with pooled-moment calculations."""

from __future__ import annotations

import math

import numpy as np

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.thresholding.estimation.models import (
    MatchedExceedanceDiagnostics,
    ThresholdSet,
    build_threshold_set,
)
from datp_core.thresholding.policies.common import BenignCalibrationScores
from datp_core.thresholding.policies.enums import ThresholdOwnerKind
from datp_core.thresholding.policies.federated import FederatedMatchedExceedanceThresholdPolicyRecord


def federated_moments(calibration: tuple[BenignCalibrationScores, ...]) -> tuple[float, float]:
    counts = np.asarray([len(item.values) for item in calibration], dtype=np.float64)
    means = np.asarray([np.mean(item.values) for item in calibration], dtype=np.float64)
    variances = np.asarray([np.var(item.values) for item in calibration], dtype=np.float64)
    total = float(np.sum(counts))
    if total <= 0.0:
        raise ValueError("Federated summary threshold has no calibration rows")
    mean = float(np.sum(counts * means) / total)
    variance = float(np.sum(counts * variances) / total + \
                     np.sum(counts * (means - mean) ** 2) / total)
    return mean, math.sqrt(variance)


def estimate_federated_matched(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    policy: FederatedMatchedExceedanceThresholdPolicyRecord,
) -> ThresholdSet:
    grid = policy.candidate_grid
    if grid.step <= 0.0:
        raise ValueError("Matched-exceedance policy has an invalid authored candidate grid")
    mean, standard_deviation = federated_moments(calibration)
    candidates = np.arange(grid.minimum, grid.maximum + grid.step / 2.0, grid.step)
    scores = np.asarray([score for item in calibration for score in item.values], dtype=np.float64)
    achieved = np.asarray([np.mean(scores > mean + candidate * standard_deviation)
                          for candidate in candidates])
    deviation = np.abs(achieved - (1.0 - target_quantile.value))
    winner = candidates[np.flatnonzero(deviation == np.min(deviation))[-1]]
    threshold = mean + float(winner) * standard_deviation
    diagnostics = MatchedExceedanceDiagnostics(
        selected_coefficient=float(winner),
        candidate_grid_minimum=grid.minimum,
        candidate_grid_maximum=grid.maximum,
        candidate_grid_step=grid.step,
        pooled_mean=float(mean),
        pooled_standard_deviation=float(standard_deviation),
        achieved_exceedance=tuple((float(c), float(a))
                                  for c, a in zip(candidates, achieved, strict=True)),
        tie_set=tuple(float(candidates[i]) for i in np.flatnonzero(deviation == np.min(deviation))),
    )
    return build_threshold_set(
        policy_id,
        calibration,
        {item.client_id.value: threshold for item in calibration},
        ThresholdOwnerKind.FEDERATED_MATCHED_EXCEEDANCE,
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
        ThresholdOwnerKind.FEDERATED_FIXED_K,
        target_quantile,
    )
