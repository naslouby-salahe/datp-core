"""Application use case for constructing threshold sets using authorized estimators."""

from __future__ import annotations

from attrs import evolve

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.identifiers import PopulationId, ThresholdPolicyId
from datp_core.domain.thresholding import BenignCalibrationScores, ThresholdSet
from datp_core.domain.values import Seed, TypedDomainRegistry
from datp_core.infrastructure.thresholding.base import ThresholdConstructionRequest, ThresholdEstimator


class ConstructThresholdsUseCase:
    """Construct threshold sets using estimators injected by the composition root.

    The estimator registry is built from infrastructure implementations in the
    composition root; this use case only depends on the Protocol, not any
    concrete estimator class.
    """

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
        quantile_override: float | None = None,
    ) -> ThresholdSet:
        estimator = self._registry.get(policy_id)
        policy = self._config.threshold_policies.get(policy_id)
        if quantile_override is not None:
            if not 0.0 < quantile_override < 1.0 or not hasattr(policy, "quantile"):
                raise ValueError("Threshold quantile override is invalid for the configured policy")
            policy = evolve(policy, quantile=quantile_override)
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
