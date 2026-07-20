"""Application use case for constructing threshold sets using authorized estimators."""

from __future__ import annotations

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.identifiers import PopulationId, ThresholdPolicyId
from datp_core.domain.thresholding import BenignCalibrationScores, ThresholdSet
from datp_core.domain.values import Seed, TypedDomainRegistry
from datp_core.infrastructure.thresholding.base import ThresholdConstructionRequest, ThresholdEstimator
from datp_core.infrastructure.thresholding.estimators import ConfiguredThresholdEstimator


def build_estimator_registry(
    config: ResolvedProjectConfiguration,
) -> TypedDomainRegistry[ThresholdPolicyId, ThresholdEstimator]:
    """Bind every estimator to its single resolved policy; no adapter-side policy values exist."""
    estimators: dict[ThresholdPolicyId, ThresholdEstimator] = {
        policy_id: ConfiguredThresholdEstimator(policy_id, policy)
        for policy_id, policy in config.threshold_policies.items()
    }
    return TypedDomainRegistry(_items=estimators)


class ConstructThresholdsUseCase:
    def __init__(
        self,
        config: ResolvedProjectConfiguration,
        registry: TypedDomainRegistry[ThresholdPolicyId, ThresholdEstimator],
    ) -> None:
        self._config = config
        self._registry = registry

    def execute(
        self,
        policy_id: ThresholdPolicyId,
        calibration: tuple[BenignCalibrationScores, ...],
        population_id: PopulationId,
        family_map: dict[str, str] | None,
        seed: Seed | None,
        selected_coefficient: float | None,
    ) -> ThresholdSet:
        estimator = self._registry.get(policy_id)
        policy = self._config.threshold_policies.get(policy_id)
        if policy is None:
            raise KeyError(f"Unknown resolved threshold policy: {policy_id.value}")
        return estimator.estimate(
            ThresholdConstructionRequest(
                policy_id=policy_id,
                policy=policy,
                calibration=calibration,
                population_id=population_id,
                family_map=family_map,
                seed=seed,
                selected_coefficient=selected_coefficient,
            )
        )
