"""Protocol interface and request payload for deterministic threshold estimators."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from attrs import define

from datp_core.config.models.protocol_config import TypedThresholdPolicyConfig
from datp_core.domain.identifiers import PopulationId, ThresholdPolicyId
from datp_core.domain.thresholding import BenignCalibrationScores, ThresholdSet
from datp_core.domain.values import Seed


@define(frozen=True, slots=True, kw_only=True)
class ThresholdConstructionRequest:
    """Request payload containing calibration scores and typed resolved policy configuration."""

    policy_id: ThresholdPolicyId
    policy: TypedThresholdPolicyConfig
    calibration: tuple[BenignCalibrationScores, ...]
    population_id: PopulationId
    family_map: dict[str, str] | None = None
    seed: Seed | None = None
    selected_coefficient: float | None = None


@runtime_checkable
class ThresholdEstimator(Protocol):
    """Protocol for a threshold policy estimator."""

    @property
    def policy_id(self) -> ThresholdPolicyId: ...

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet: ...
