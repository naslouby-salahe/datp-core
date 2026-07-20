"""Protocol interface for deterministic threshold estimators."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ...domain.identifiers import ThresholdPolicyId
from ...domain.thresholding import BenignCalibrationScores, ThresholdSet
from ...domain.values import Probability


@runtime_checkable
class ThresholdEstimator(Protocol):
    """Protocol for a threshold policy estimator."""

    @property
    def policy_id(self) -> ThresholdPolicyId: ...

    def estimate(
        self,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability,
        **kwargs: object,
    ) -> ThresholdSet: ...
