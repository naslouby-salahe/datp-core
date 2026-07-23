"""Split-conformal (B2-conf) local threshold estimation."""

from __future__ import annotations

import math

import numpy as np

from datp_core.thresholding.models import (
    BenignCalibrationScores,
    ConformalAttainabilityStatus,
    Probability,
    SplitConformalThresholdPolicyRecord,
    ThresholdPolicyId,
    ThresholdSet,
    build_threshold_set,
)


def estimate_conformal(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    target_quantile: Probability,
    policy: SplitConformalThresholdPolicyRecord,
) -> ThresholdSet:
    thresholds: dict[str, float] = {}
    ranks: dict[str, int] = {}
    for item in calibration:
        scores = np.sort(np.asarray(item.values, dtype=np.float64))
        if len(scores) < policy.minimum_sample_count:
            raise ValueError("Conformal threshold is unattainable for the authored minimum sample count")
        rank = min(math.ceil((len(scores) + 1) * (1.0 - policy.coverage_alpha)), len(scores))
        thresholds[item.client_id.value] = float(scores[rank - 1])
        ranks[item.client_id.value] = rank
    return build_threshold_set(
        policy_id,
        calibration,
        thresholds,
        "split_conformal",
        target_quantile,
        conformal_ranks=ranks,
        conformal_attainability={item.client_id.value: ConformalAttainabilityStatus.ATTAINABLE for item in calibration},
    )
