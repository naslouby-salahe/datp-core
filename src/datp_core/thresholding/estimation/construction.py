"""ConstructThresholdsUseCase — threshold construction orchestration with override support."""

from __future__ import annotations

from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import PopulationId, ThresholdPolicyId
from datp_core.core.registry import TypedDomainRegistry
from datp_core.thresholding.estimation.models import ThresholdConstructionRequest, ThresholdSet
from datp_core.thresholding.estimation.ports import ThresholdEstimator
from datp_core.thresholding.policies.clustering import ClusterThresholdPolicyRecord
from datp_core.thresholding.policies.common import BenignCalibrationScores
from datp_core.thresholding.policies.union import ThresholdPolicyRecord


def _has_quantile(policy: ThresholdPolicyRecord) -> bool:
    return hasattr(policy, "quantile")


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
        selected_coefficient: float | None,
        quantile_override: float | None = None,
        fingerprint_features_override: tuple[str, ...] | None = None,
    ) -> ThresholdSet:
        estimator = self._registry.get(policy_id)
        policy = self._config.threshold_policies.get(policy_id)
        if quantile_override is not None:
            if not 0.0 < quantile_override < 1.0 or not _has_quantile(policy):
                raise ValueError("Threshold quantile override is invalid for the configured policy")
            policy = policy.model_copy(update={"quantile": quantile_override})
        if fingerprint_features_override is not None:
            if (
                not isinstance(policy, ClusterThresholdPolicyRecord)
                or not fingerprint_features_override
                or any(feature not in policy.fingerprint.features for feature in fingerprint_features_override)
            ):
                raise ValueError("Fingerprint-feature override is invalid for the configured cluster policy")
            updated_fingerprint = policy.fingerprint.model_copy(update={"features": fingerprint_features_override})
            policy = policy.model_copy(update={"fingerprint": updated_fingerprint})
        return estimator.estimate(
            ThresholdConstructionRequest(
                policy_id=policy_id,
                policy=policy,
                calibration=calibration,
                population_id=population_id,
                family_map=family_map,
                selected_coefficient=selected_coefficient,
            )
        )
