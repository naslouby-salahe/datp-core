"""Family-mean threshold estimator (B3)."""

from __future__ import annotations

import numpy as np

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.thresholding.estimation.models import ThresholdSet, build_threshold_set
from datp_core.thresholding.policies.common import BenignCalibrationScores
from datp_core.thresholding.policies.enums import ThresholdOwnerKind


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
    thresholds = {item.client_id.value: family_thresholds[family_map[item.client_id.value]] for item in calibration}
    return build_threshold_set(policy_id, calibration, thresholds, ThresholdOwnerKind.FAMILY_MEAN, target_quantile)
