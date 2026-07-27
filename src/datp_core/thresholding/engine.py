"""ThresholdEngine — single exhaustive match dispatch over ThresholdPolicyKind."""

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
    ThresholdSet,
    UnsupportedThresholdPolicyError,
)
from datp_core.thresholding.policies import (
    CalibrationFallbackPolicy,
    ClusterPolicy,
    ConformalPolicy,
    FederatedFixedPolicy,
    FederatedMatchedPolicy,
    FixedShrinkagePolicy,
    QuantilePolicy,
)


class ThresholdEngine:
    """Construct thresholds from a resolved policy and calibration data.

    Dispatches exhaustively by ThresholdPolicyKind. No registry, no protocol,
    no runtime policy mutation, no late validation of already-guaranteed fields.
    """

    def construct(self, request: ThresholdConstructionRequest) -> ThresholdSet:
        if not request.calibration:
            raise EmptyCalibrationError("Threshold construction requires at least one eligible client")

        policy = request.policy

        match policy.kind:
            case ThresholdPolicyKind.SHARED_MEAN:
                assert isinstance(policy, QuantilePolicy)
                return estimate_shared_mean(request.policy_id, request.calibration, Probability(policy.quantile))
            case ThresholdPolicyKind.SHARED_POOLED:
                assert isinstance(policy, QuantilePolicy)
                return estimate_pooled(request.policy_id, request.calibration, Probability(policy.quantile))
            case ThresholdPolicyKind.SHARED_WEIGHTED:
                assert isinstance(policy, QuantilePolicy)
                return estimate_shared_weighted(request.policy_id, request.calibration, Probability(policy.quantile))
            case ThresholdPolicyKind.LOCAL_QUANTILE:
                assert isinstance(policy, QuantilePolicy)
                return estimate_local_quantile(request.policy_id, request.calibration, Probability(policy.quantile))
            case ThresholdPolicyKind.FAMILY_MEAN:
                assert isinstance(policy, QuantilePolicy)
                if request.family_assignments is None:
                    raise EmptyCalibrationError("Family-mean threshold requires family assignments")
                return estimate_family_mean(
                    request.policy_id,
                    request.calibration,
                    Probability(policy.quantile),
                    request.family_assignments,
                    quantile_fn=quantile,
                )
            case ThresholdPolicyKind.CLUSTER:
                assert isinstance(policy, ClusterPolicy)
                return estimate_cluster(
                    request.policy_id,
                    request.calibration,
                    Probability(policy.quantile),
                    cluster_count=policy.cluster_count,
                    aggregation=policy.aggregation,
                    fingerprint_features=policy.fingerprint_features,
                    kmeans_random_seed=policy.kmeans_random_seed,
                    kmeans_initialization_runs=policy.kmeans_initialization_runs,
                    kmeans_maximum_iterations=policy.kmeans_maximum_iterations,
                    kmeans_convergence_tolerance=policy.kmeans_convergence_tolerance,
                    quantile_fn=quantile,
                )
            case ThresholdPolicyKind.CONFORMAL:
                assert isinstance(policy, ConformalPolicy)
                return estimate_conformal(
                    request.policy_id,
                    request.calibration,
                    coverage_alpha=policy.coverage_alpha,
                    minimum_sample_count=policy.minimum_sample_count,
                )
            case ThresholdPolicyKind.SHRINKAGE:
                assert isinstance(policy, FixedShrinkagePolicy)
                return estimate_shrinkage(
                    request.policy_id,
                    request.calibration,
                    Probability(policy.quantile),
                    policy.shrinkage_weight,
                )
            case ThresholdPolicyKind.CALIBRATION_FALLBACK:
                assert isinstance(policy, CalibrationFallbackPolicy)
                return estimate_calibration_fallback(
                    request.policy_id,
                    request.calibration,
                    Probability(policy.quantile),
                    policy.n_half,
                )
            case ThresholdPolicyKind.FEDERATED_MATCHED:
                assert isinstance(policy, FederatedMatchedPolicy)
                return estimate_federated_matched(
                    request.policy_id,
                    request.calibration,
                    Probability(policy.quantile),
                    grid_minimum=policy.candidate_grid_minimum,
                    grid_maximum=policy.candidate_grid_maximum,
                    grid_step=policy.candidate_grid_step,
                )
            case ThresholdPolicyKind.FEDERATED_FIXED:
                assert isinstance(policy, FederatedFixedPolicy)
                return estimate_federated_fixed(
                    request.policy_id,
                    request.calibration,
                    Probability(policy.quantile),
                    policy.fixed_coefficient,
                )
            case _:
                raise UnsupportedThresholdPolicyError(f"No estimator for threshold policy kind: {policy.kind.value}")
