"""Split-conformal threshold estimator with finite-sample rank rule."""

from __future__ import annotations

import math

import numpy as np

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.thresholding.estimation.models import ThresholdSet, build_threshold_set
from datp_core.thresholding.policies.common import BenignCalibrationScores
from datp_core.thresholding.policies.conformal import SplitConformalThresholdPolicyRecord
from datp_core.thresholding.policies.enums import ConformalAttainabilityStatus, ThresholdOwnerKind


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
            raise ValueError(
                "Conformal threshold is unattainable for the authored minimum sample count")
        rank = min(math.ceil((len(scores) + 1) * (1.0 - policy.coverage_alpha)), len(scores))
        thresholds[item.client_id.value] = float(scores[rank - 1])
        ranks[item.client_id.value] = rank
    return build_threshold_set(
        policy_id,
        calibration,
        thresholds,
        ThresholdOwnerKind.SPLIT_CONFORMAL,
        target_quantile,
        conformal_ranks=ranks,
        conformal_attainability={
            item.client_id.value: ConformalAttainabilityStatus.ATTAINABLE for item in calibration},
    )
