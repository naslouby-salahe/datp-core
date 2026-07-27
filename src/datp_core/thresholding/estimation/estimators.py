"""Per-kind threshold estimator implementations and registry.

Each estimator implements the ThresholdEstimator protocol and delegates to existing
pure estimation functions without changing any threshold formulas.  The
ThresholdEstimatorRegistry maps ThresholdPolicyKind members to their concrete
estimator class, replacing the previous isinstance dispatch chain.
"""

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
from datp_core.thresholding.policies.enums import ThresholdPolicyKind
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

# ---------------------------------------------------------------------------
# Private base with shared boilerplate
# ---------------------------------------------------------------------------


class _EstimatorBase:
    """Shared constructor, policy_id property, validation, and local-quantile computation.

    Subclasses only override ``estimate()`` to call their specific estimation function.
    """

    def __init__(self, policy_id: ThresholdPolicyId, policy: ThresholdPolicyRecord) -> None:
        self._policy_id = policy_id
        self._policy = policy

    @property
    def policy_id(self) -> ThresholdPolicyId:
        return self._policy_id

    def _validate(self, request: ThresholdConstructionRequest) -> None:
        if request.policy_id != self._policy_id:
            raise ValueError("Threshold estimator request does not match its resolved policy kind")
        if not request.calibration:
            raise ValueError("Threshold construction requires at least one eligible client")

    @staticmethod
    def _local_quantiles(
        calibration: tuple[ThresholdConstructionRequest, ...],
        target_quantile: object,
    ) -> dict[str, float]:
        return {item.client_id.value: quantile(item.values, target_quantile.value) for item in calibration}


# ---------------------------------------------------------------------------
# Per-kind estimator classes
# ---------------------------------------------------------------------------


class SharedMeanEstimator(_EstimatorBase):
    """Threshold estimator for ThresholdPolicyKind.SHARED_MEAN."""

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        self._validate(request)
        target_quantile = policy_quantile(request.policy)
        local = self._local_quantiles(request.calibration, target_quantile)
        return estimate_shared_mean(self._policy_id, request.calibration, local, target_quantile)


class PooledEstimator(_EstimatorBase):
    """Threshold estimator for ThresholdPolicyKind.SHARED_POOLED."""

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        self._validate(request)
        target_quantile = policy_quantile(request.policy)
        local = self._local_quantiles(request.calibration, target_quantile)
        return estimate_pooled(self._policy_id, request.calibration, local, target_quantile, quantile)


class SharedWeightedEstimator(_EstimatorBase):
    """Threshold estimator for ThresholdPolicyKind.SHARED_WEIGHTED."""

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        self._validate(request)
        target_quantile = policy_quantile(request.policy)
        local = self._local_quantiles(request.calibration, target_quantile)
        return estimate_shared_weighted(self._policy_id, request.calibration, local, target_quantile)


class LocalQuantileEstimator(_EstimatorBase):
    """Threshold estimator for ThresholdPolicyKind.LOCAL_QUANTILE."""

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        self._validate(request)
        target_quantile = policy_quantile(request.policy)
        local = self._local_quantiles(request.calibration, target_quantile)
        return estimate_local_quantile(self._policy_id, request.calibration, local, target_quantile)


class FamilyMeanEstimator(_EstimatorBase):
    """Threshold estimator for ThresholdPolicyKind.FAMILY_MEAN."""

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        self._validate(request)
        target_quantile = policy_quantile(request.policy)
        local = self._local_quantiles(request.calibration, target_quantile)
        return estimate_family_mean(self._policy_id, request.calibration, local, target_quantile, request.family_map)


class ClusterEstimator(_EstimatorBase):
    """Threshold estimator for ThresholdPolicyKind.CLUSTER."""

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        self._validate(request)
        target_quantile = policy_quantile(request.policy)
        local = self._local_quantiles(request.calibration, target_quantile)
        return estimate_cluster(self._policy_id, request.calibration, local, target_quantile, request.policy, quantile)


class ConformalEstimator(_EstimatorBase):
    """Threshold estimator for ThresholdPolicyKind.CONFORMAL."""

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        self._validate(request)
        target_quantile = policy_quantile(request.policy)
        return estimate_conformal(self._policy_id, request.calibration, target_quantile, request.policy)


class ShrinkageEstimator(_EstimatorBase):
    """Threshold estimator for ThresholdPolicyKind.SHRINKAGE."""

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        self._validate(request)
        target_quantile = policy_quantile(request.policy)
        local = self._local_quantiles(request.calibration, target_quantile)
        coefficient = (
            request.policy.shrinkage_weight
            if request.policy.shrinkage_weight is not None
            else request.selected_coefficient
        )
        if coefficient is None:
            raise ValueError("Shrinkage threshold requires an experiment-selected coefficient")
        return estimate_shrinkage(self._policy_id, request.calibration, local, target_quantile, coefficient)


class CalibrationFallbackEstimator(_EstimatorBase):
    """Threshold estimator for ThresholdPolicyKind.CALIBRATION_FALLBACK."""

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        self._validate(request)
        target_quantile = policy_quantile(request.policy)
        local = self._local_quantiles(request.calibration, target_quantile)
        return estimate_calibration_fallback(
            self._policy_id, request.calibration, local, target_quantile, request.policy
        )


class FederatedMatchedEstimator(_EstimatorBase):
    """Threshold estimator for ThresholdPolicyKind.FEDERATED_MATCHED."""

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        self._validate(request)
        target_quantile = policy_quantile(request.policy)
        return estimate_federated_matched(self._policy_id, request.calibration, target_quantile, request.policy)


class FederatedFixedEstimator(_EstimatorBase):
    """Threshold estimator for ThresholdPolicyKind.FEDERATED_FIXED."""

    def estimate(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        self._validate(request)
        target_quantile = policy_quantile(request.policy)
        coefficient = request.policy.fixed_k if request.policy.fixed_k is not None else request.selected_coefficient
        if coefficient is None:
            raise ValueError("Fixed-k threshold requires an experiment-selected coefficient")
        return estimate_federated_fixed(self._policy_id, request.calibration, target_quantile, coefficient)


# ---------------------------------------------------------------------------
# Type-to-kind mapping
# ---------------------------------------------------------------------------

_POLICY_TYPE_TO_KIND: dict[type, ThresholdPolicyKind] = {
    SharedMeanThresholdPolicyRecord: ThresholdPolicyKind.SHARED_MEAN,
    SharedPooledThresholdPolicyRecord: ThresholdPolicyKind.SHARED_POOLED,
    CentralizedPooledThresholdPolicyRecord: ThresholdPolicyKind.SHARED_POOLED,
    SharedWeightedThresholdPolicyRecord: ThresholdPolicyKind.SHARED_WEIGHTED,
    LocalQuantileThresholdPolicyRecord: ThresholdPolicyKind.LOCAL_QUANTILE,
    FamilyMeanThresholdPolicyRecord: ThresholdPolicyKind.FAMILY_MEAN,
    ClusterThresholdPolicyRecord: ThresholdPolicyKind.CLUSTER,
    SplitConformalThresholdPolicyRecord: ThresholdPolicyKind.CONFORMAL,
    LocalGlobalShrinkageThresholdPolicyRecord: ThresholdPolicyKind.SHRINKAGE,
    CalibrationFallbackThresholdPolicyRecord: ThresholdPolicyKind.CALIBRATION_FALLBACK,
    FederatedMatchedExceedanceThresholdPolicyRecord: ThresholdPolicyKind.FEDERATED_MATCHED,
    FederatedFixedCoefficientThresholdPolicyRecord: ThresholdPolicyKind.FEDERATED_FIXED,
}


# ---------------------------------------------------------------------------
# ThresholdEstimatorRegistry
# ---------------------------------------------------------------------------


class ThresholdEstimatorRegistry:
    """Maps ThresholdPolicyKind to concrete estimator classes.

    Registration is performed at module level after every per-kind class definition.
    """

    def __init__(self) -> None:
        self._kind_map: dict[ThresholdPolicyKind, type[ThresholdEstimator]] = {}

    def register(self, kind: ThresholdPolicyKind, estimator_cls: type[ThresholdEstimator]) -> None:
        """Register an estimator class for a given policy kind."""
        self._kind_map[kind] = estimator_cls

    def create(
        self,
        policy_id: ThresholdPolicyId,
        policy: ThresholdPolicyRecord,
    ) -> ThresholdEstimator:
        """Determine the policy kind from the record type and instantiate the matching estimator."""
        type_key = type(policy)
        kind = _POLICY_TYPE_TO_KIND.get(type_key)
        if kind is None:
            raise TypeError(f"Unsupported threshold policy configuration: {type_key.__name__}")
        estimator_cls = self._kind_map.get(kind)
        if estimator_cls is None:
            raise ValueError(f"No estimator registered for threshold policy kind: {kind.value}")
        return estimator_cls(policy_id, policy)


# Module-level singleton registry populated with every per-kind class.
ESTIMATOR_KIND_REGISTRY = ThresholdEstimatorRegistry()
ESTIMATOR_KIND_REGISTRY.register(ThresholdPolicyKind.SHARED_MEAN, SharedMeanEstimator)
ESTIMATOR_KIND_REGISTRY.register(ThresholdPolicyKind.SHARED_POOLED, PooledEstimator)
ESTIMATOR_KIND_REGISTRY.register(ThresholdPolicyKind.SHARED_WEIGHTED, SharedWeightedEstimator)
ESTIMATOR_KIND_REGISTRY.register(ThresholdPolicyKind.LOCAL_QUANTILE, LocalQuantileEstimator)
ESTIMATOR_KIND_REGISTRY.register(ThresholdPolicyKind.FAMILY_MEAN, FamilyMeanEstimator)
ESTIMATOR_KIND_REGISTRY.register(ThresholdPolicyKind.CLUSTER, ClusterEstimator)
ESTIMATOR_KIND_REGISTRY.register(ThresholdPolicyKind.CONFORMAL, ConformalEstimator)
ESTIMATOR_KIND_REGISTRY.register(ThresholdPolicyKind.SHRINKAGE, ShrinkageEstimator)
ESTIMATOR_KIND_REGISTRY.register(ThresholdPolicyKind.CALIBRATION_FALLBACK, CalibrationFallbackEstimator)
ESTIMATOR_KIND_REGISTRY.register(ThresholdPolicyKind.FEDERATED_MATCHED, FederatedMatchedEstimator)
ESTIMATOR_KIND_REGISTRY.register(ThresholdPolicyKind.FEDERATED_FIXED, FederatedFixedEstimator)


__all__ = [
    "ESTIMATOR_KIND_REGISTRY",
    "ThresholdEstimatorRegistry",
]
