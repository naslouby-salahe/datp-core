"""Threshold estimator protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.thresholding.estimation.models import ThresholdConstructionRequest, ThresholdSet
from datp_core.thresholding.policies.union import ThresholdPolicyRecord


@runtime_checkable
class ThresholdEstimator(Protocol):
    def __init__(self, policy_id: ThresholdPolicyId, policy: ThresholdPolicyRecord) -> None: ...

    @property
    def policy_id(self) -> ThresholdPolicyId: ...

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet: ...
