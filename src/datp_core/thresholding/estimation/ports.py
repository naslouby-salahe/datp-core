"""Threshold estimator protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.thresholding.estimation.models import ThresholdConstructionRequest, ThresholdSet


@runtime_checkable
class ThresholdEstimator(Protocol):
    @property
    def policy_id(self) -> ThresholdPolicyId: ...

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet: ...
