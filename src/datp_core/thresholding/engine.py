"""ThresholdEngine — single exhaustive dispatch over ThresholdPolicyKind."""

from __future__ import annotations

from datp_core.core.numbers import Probability
from datp_core.thresholding.enums import ThresholdPolicyKind
from datp_core.thresholding.estimators.federated import (
    estimate_federated_fixed,
    estimate_federated_matched,
)
from datp_core.thresholding.estimators.grouped import (
    estimate_cluster,
    estimate_family_mean,
)
from datp_core.thresholding.estimators.quantile import (
    estimate_calibration_fallback,
    estimate_conformal,
    estimate_local_quantile,
    estimate_pooled,
    estimate_shared_mean,
    estimate_shared_weighted,
    estimate_shrinkage,
    quantile,
)
from datp_core.thresholding.models import (
    EmptyCalibrationError,
    ThresholdConstructionRequest,
    ThresholdingError,
    ThresholdSet,
    UnsupportedThresholdPolicyError,
)
from datp_core.thresholding.policies import (
    ClusterPolicy,
    ConformalPolicy,
    FederatedPolicy,
    ShrinkagePolicy,
)


class ThresholdEngine:
    """Construct thresholds from a resolved policy and calibration data.

    Dispatches exhaustively by ThresholdPolicyKind. No registry, no protocol,
    no runtime policy mutation.
    """

    def construct(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        if not request.calibration:
            raise EmptyCalibrationError("Threshold construction requires at least one eligible client")
        _validate_request_policy_match(request)

        policy = request.policy
        target = Probability(policy.quantile) if hasattr(policy, "quantile") else None

        kind = policy.kind
        if kind == ThresholdPolicyKind.SHARED_MEAN:
            return estimate_shared_mean(request.policy_id, request.calibration, target)
        elif kind == ThresholdPolicyKind.SHARED_POOLED:
            return estimate_pooled(request.policy_id, request.calibration, target)
        elif kind == ThresholdPolicyKind.SHARED_WEIGHTED:
            return estimate_shared_weighted(request.policy_id, request.calibration, target)
        elif kind == ThresholdPolicyKind.LOCAL_QUANTILE:
            return estimate_local_quantile(request.policy_id, request.calibration, target)
        elif kind == ThresholdPolicyKind.FAMILY_MEAN:
            if request.family_assignments is None:
                raise ThresholdingError("Family-mean threshold requires family assignments")
            return estimate_family_mean(
                request.policy_id,
                request.calibration,
                target,
                request.family_assignments,
                quantile_fn=quantile,
            )
        elif kind == ThresholdPolicyKind.CLUSTER:
            cluster_policy = request.policy
            assert isinstance(cluster_policy, ClusterPolicy)
            return estimate_cluster(
                request.policy_id,
                request.calibration,
                target,
                cluster_count=cluster_policy.cluster_count,
                aggregation=cluster_policy.aggregation,
                fingerprint_features=cluster_policy.fingerprint_features,
                kmeans_random_seed=cluster_policy.kmeans_random_seed,
                kmeans_initialization_runs=cluster_policy.kmeans_initialization_runs,
                kmeans_maximum_iterations=cluster_policy.kmeans_maximum_iterations,
                kmeans_convergence_tolerance=cluster_policy.kmeans_convergence_tolerance,
                quantile_fn=quantile,
            )
        elif kind == ThresholdPolicyKind.CONFORMAL:
            conf_policy = request.policy
            assert isinstance(conf_policy, ConformalPolicy)
            return estimate_conformal(
                request.policy_id,
                request.calibration,
                coverage_alpha=conf_policy.coverage_alpha,
                minimum_sample_count=conf_policy.minimum_sample_count,
            )
        elif kind == ThresholdPolicyKind.SHRINKAGE:
            shrink_policy = request.policy
            assert isinstance(shrink_policy, ShrinkagePolicy)
            if shrink_policy.shrinkage_weight is None:
                raise ThresholdingError("Shrinkage policy requires a resolved shrinkage weight")
            return estimate_shrinkage(
                request.policy_id,
                request.calibration,
                target,
                shrink_policy.shrinkage_weight,
            )
        elif kind == ThresholdPolicyKind.CALIBRATION_FALLBACK:
            fallback_policy = request.policy
            assert isinstance(fallback_policy, ShrinkagePolicy)
            if fallback_policy.n_half is None:
                raise ThresholdingError("Calibration fallback policy requires a resolved n_half")
            return estimate_calibration_fallback(
                request.policy_id,
                request.calibration,
                target,
                fallback_policy.n_half,
            )
        elif kind == ThresholdPolicyKind.FEDERATED_MATCHED:
            fed_policy = request.policy
            assert isinstance(fed_policy, FederatedPolicy)
            if (
                fed_policy.candidate_grid_minimum is None
                or fed_policy.candidate_grid_maximum is None
                or fed_policy.candidate_grid_step is None
            ):
                raise ThresholdingError("Federated matched policy requires a complete candidate grid")
            return estimate_federated_matched(
                request.policy_id,
                request.calibration,
                target,
                grid_minimum=fed_policy.candidate_grid_minimum,
                grid_maximum=fed_policy.candidate_grid_maximum,
                grid_step=fed_policy.candidate_grid_step,
            )
        elif kind == ThresholdPolicyKind.FEDERATED_FIXED:
            fed_policy = request.policy
            assert isinstance(fed_policy, FederatedPolicy)
            if fed_policy.fixed_k is None:
                raise ThresholdingError("Federated fixed policy requires a resolved fixed_k")
            return estimate_federated_fixed(
                request.policy_id,
                request.calibration,
                target,
                fed_policy.fixed_k,
            )
        else:
            raise UnsupportedThresholdPolicyError(f"No estimator for threshold policy kind: {kind.value}")


def _validate_request_policy_match(request: ThresholdConstructionRequest) -> None:
    """Ensure request and policy identifiers are consistent."""
    if request.policy_id != request.policy_id:
        raise ThresholdingError("Policy ID mismatch in construction request")
    if not request.calibration:
        raise EmptyCalibrationError("Calibration is empty")
