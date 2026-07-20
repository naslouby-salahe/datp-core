"""Application use case for constructing threshold sets using authorized estimators."""

from __future__ import annotations

from typing import Any

from datp_core.domain.identifiers import ThresholdPolicyId
from datp_core.domain.thresholding import BenignCalibrationScores, ThresholdSet
from datp_core.domain.values import Probability, TypedDomainRegistry
from datp_core.infrastructure.thresholding.base import ThresholdEstimator
from datp_core.infrastructure.thresholding.estimators import (
    CalibrationFallbackEstimator,
    ClusterThresholdEstimator,
    FamilyMeanThresholdEstimator,
    FederatedFixedCoefficientEstimator,
    FederatedMatchedExceedanceEstimator,
    LocalGlobalShrinkageEstimator,
    LocalQuantileThresholdEstimator,
    PooledThresholdEstimator,
    SharedMeanThresholdEstimator,
    SplitConformalThresholdEstimator,
    WeightedSharedThresholdEstimator,
)

DEFAULT_Q = Probability(0.95)


def build_estimator_registry() -> TypedDomainRegistry[ThresholdPolicyId, ThresholdEstimator]:
    estimators: list[ThresholdEstimator] = [
        SharedMeanThresholdEstimator(),
        PooledThresholdEstimator("shared_pooled_p95"),
        PooledThresholdEstimator("centralized_pooled_p95"),
        WeightedSharedThresholdEstimator(),
        LocalQuantileThresholdEstimator(),
        FamilyMeanThresholdEstimator(),
        ClusterThresholdEstimator("cluster_k3_mean_p95", k_clusters=3, use_median=False),
        ClusterThresholdEstimator("cluster_k9_mean_p95", k_clusters=9, use_median=False),
        ClusterThresholdEstimator("cluster_k3_robust_median_p95", k_clusters=3, use_median=True),
        SplitConformalThresholdEstimator(),
        LocalGlobalShrinkageEstimator(),
        CalibrationFallbackEstimator(),
        FederatedMatchedExceedanceEstimator(),
        FederatedFixedCoefficientEstimator(),
    ]
    return TypedDomainRegistry(_items={est.policy_id: est for est in estimators})


class ConstructThresholdsUseCase:
    def __init__(self, registry: TypedDomainRegistry[ThresholdPolicyId, ThresholdEstimator] | None = None) -> None:
        self._registry = registry or build_estimator_registry()

    def execute(
        self,
        policy_id: ThresholdPolicyId,
        calibration: tuple[BenignCalibrationScores, ...],
        quantile: Probability = DEFAULT_Q,
        **kwargs: Any,
    ) -> ThresholdSet:
        estimator = self._registry.get(policy_id)
        return estimator.estimate(calibration, quantile, **kwargs)
