"""Configured threshold estimator dispatch across all 12 policy families."""

from __future__ import annotations

from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.thresholding.estimation.clustering import estimate_cluster
from datp_core.thresholding.estimation.conformal import estimate_conformal
from datp_core.thresholding.estimation.federated import estimate_federated_fixed, estimate_federated_matched
from datp_core.thresholding.estimation.grouped import estimate_family_mean
from datp_core.thresholding.estimation.models import ThresholdConstructionRequest, ThresholdSet
from datp_core.thresholding.estimation.ports import ThresholdEstimator
from datp_core.thresholding.estimation.quantiles import (
    estimate_local_quantile,
    estimate_pooled,
    estimate_shared_mean,
    estimate_shared_weighted,
    policy_quantile,
    quantile,
)
from datp_core.thresholding.estimation.shrinkage import estimate_calibration_fallback, estimate_shrinkage
from datp_core.thresholding.policies.clustering import ClusterThresholdPolicyRecord
from datp_core.thresholding.policies.conformal import SplitConformalThresholdPolicyRecord
from datp_core.thresholding.policies.federated import (
    FederatedFixedCoefficientThresholdPolicyRecord,
    FederatedMatchedExceedanceThresholdPolicyRecord,
)
from datp_core.thresholding.policies.grouped import FamilyMeanThresholdPolicyRecord
from datp_core.thresholding.policies.shared import (
    CentralizedPooledThresholdPolicyRecord,
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
)
from datp_core.thresholding.policies.shrinkage import (
    CalibrationFallbackThresholdPolicyRecord,
    LocalGlobalShrinkageThresholdPolicyRecord,
)
from datp_core.thresholding.policies.union import ThresholdPolicyRecord


class ConfiguredThresholdEstimator(ThresholdEstimator):
    def __init__(self, policy_id: ThresholdPolicyId, policy: ThresholdPolicyRecord) -> None:
        self._policy_id = policy_id
        self._policy = policy

    @property
    def policy_id(self) -> ThresholdPolicyId:
        return self._policy_id

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        if request.policy_id != self._policy_id or type(request.policy) is not type(self._policy):
            raise ValueError("Threshold estimator request does not match its resolved policy kind")
        calibration = request.calibration
        if not calibration:
            raise ValueError("Threshold construction requires at least one eligible client")
        policy = request.policy
        target_quantile = policy_quantile(policy)
        local = {item.client_id.value: quantile(
            item.values, target_quantile.value) for item in calibration}

        if isinstance(policy, SharedMeanThresholdPolicyRecord):
            return estimate_shared_mean(self._policy_id, calibration, local, target_quantile)
        if isinstance(policy, (SharedPooledThresholdPolicyRecord, CentralizedPooledThresholdPolicyRecord)):
            return estimate_pooled(self._policy_id, calibration, local, target_quantile, quantile)
        if isinstance(policy, SharedWeightedThresholdPolicyRecord):
            return estimate_shared_weighted(self._policy_id, calibration, local, target_quantile)
        if isinstance(policy, LocalQuantileThresholdPolicyRecord):
            return estimate_local_quantile(self._policy_id, calibration, local, target_quantile)
        if isinstance(policy, FamilyMeanThresholdPolicyRecord):
            return estimate_family_mean(self._policy_id, calibration, local, target_quantile, request.family_map)
        if isinstance(policy, ClusterThresholdPolicyRecord):
            return estimate_cluster(self._policy_id, calibration, local, target_quantile, policy, quantile)
        if isinstance(policy, SplitConformalThresholdPolicyRecord):
            return estimate_conformal(self._policy_id, calibration, target_quantile, policy)
        if isinstance(policy, LocalGlobalShrinkageThresholdPolicyRecord):
            coefficient = (
                policy.shrinkage_weight if policy.shrinkage_weight is not None else request.selected_coefficient
            )
            if coefficient is None:
                raise ValueError("Shrinkage threshold requires an experiment-selected coefficient")
            return estimate_shrinkage(self._policy_id, calibration, local, target_quantile, coefficient)
        if isinstance(policy, CalibrationFallbackThresholdPolicyRecord):
            return estimate_calibration_fallback(self._policy_id, calibration, local, target_quantile, policy)
        if isinstance(policy, FederatedMatchedExceedanceThresholdPolicyRecord):
            return estimate_federated_matched(self._policy_id, calibration, target_quantile, policy)
        if isinstance(policy, FederatedFixedCoefficientThresholdPolicyRecord):
            coefficient = policy.fixed_k if policy.fixed_k is not None else request.selected_coefficient
            if coefficient is None:
                raise ValueError("Fixed-k threshold requires an experiment-selected coefficient")
            return estimate_federated_fixed(self._policy_id, calibration, target_quantile, coefficient)
        raise TypeError(f"Unsupported threshold policy configuration: {type(policy).__name__}")
