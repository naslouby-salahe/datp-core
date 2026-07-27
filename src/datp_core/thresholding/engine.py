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
)
from datp_core.thresholding.models import (
    EmptyCalibrationError,
    ThresholdConfigurationError,
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

        match policy:
            case QuantilePolicy(kind=ThresholdPolicyKind.SHARED_MEAN, quantile=quantile):
                return estimate_shared_mean(request.policy_id, request.calibration, Probability(quantile))
            case QuantilePolicy(kind=ThresholdPolicyKind.SHARED_POOLED, quantile=quantile):
                return estimate_pooled(request.policy_id, request.calibration, Probability(quantile))
            case QuantilePolicy(kind=ThresholdPolicyKind.SHARED_WEIGHTED, quantile=quantile):
                return estimate_shared_weighted(request.policy_id, request.calibration, Probability(quantile))
            case QuantilePolicy(kind=ThresholdPolicyKind.LOCAL_QUANTILE, quantile=quantile):
                return estimate_local_quantile(request.policy_id, request.calibration, Probability(quantile))
            case QuantilePolicy(kind=ThresholdPolicyKind.FAMILY_MEAN, quantile=quantile):
                if request.family_assignments is None:
                    raise ThresholdConfigurationError("Family-mean threshold requires family assignments")
                fam = request.family_assignments
                cal_ids = {c.client_id for c in request.calibration}
                assigned_ids = {cid for cid, _ in fam.mapping}
                missing = cal_ids - assigned_ids
                if missing:
                    raise ThresholdConfigurationError(
                        f"Calibration clients missing from family assignments: {[str(c) for c in sorted(missing)]}"
                    )
                extra = assigned_ids - cal_ids
                if extra:
                    raise ThresholdConfigurationError(
                        f"Family assignments for clients not in calibration: {[str(c) for c in sorted(extra)]}"
                    )
                return estimate_family_mean(
                    request.policy_id,
                    request.calibration,
                    Probability(quantile),
                    request.family_assignments,
                )
            case ClusterPolicy(
                kind=ThresholdPolicyKind.CLUSTER,
                quantile=quantile,
                fingerprint_quantile=fingerprint_quantile,
                cluster_count=cluster_count,
                aggregation=aggregation,
                fingerprint_features=fingerprint_features,
                kmeans_random_seed=kmeans_random_seed,
                kmeans_initialization_runs=kmeans_initialization_runs,
                kmeans_maximum_iterations=kmeans_maximum_iterations,
                kmeans_convergence_tolerance=kmeans_convergence_tolerance,
            ):
                return estimate_cluster(
                    request.policy_id,
                    request.calibration,
                    Probability(quantile),
                    cluster_count=cluster_count,
                    aggregation=aggregation,
                    fingerprint_features=fingerprint_features,
                    fingerprint_quantile=fingerprint_quantile,
                    kmeans_random_seed=kmeans_random_seed,
                    kmeans_initialization_runs=kmeans_initialization_runs,
                    kmeans_maximum_iterations=kmeans_maximum_iterations,
                    kmeans_convergence_tolerance=kmeans_convergence_tolerance,
                )
            case ConformalPolicy(
                kind=ThresholdPolicyKind.CONFORMAL,
                coverage_alpha=coverage_alpha,
                minimum_sample_count=minimum_sample_count,
            ):
                return estimate_conformal(
                    request.policy_id,
                    request.calibration,
                    coverage_alpha=coverage_alpha,
                    minimum_sample_count=minimum_sample_count,
                )
            case FixedShrinkagePolicy(
                kind=ThresholdPolicyKind.SHRINKAGE, quantile=quantile, shrinkage_weight=shrinkage_weight
            ):
                return estimate_shrinkage(
                    request.policy_id,
                    request.calibration,
                    Probability(quantile),
                    shrinkage_weight,
                )
            case CalibrationFallbackPolicy(
                kind=ThresholdPolicyKind.CALIBRATION_FALLBACK, quantile=quantile, n_half=n_half
            ):
                return estimate_calibration_fallback(
                    request.policy_id,
                    request.calibration,
                    Probability(quantile),
                    n_half,
                )
            case FederatedMatchedPolicy(
                kind=ThresholdPolicyKind.FEDERATED_MATCHED,
                quantile=quantile,
                candidate_grid_minimum=candidate_grid_minimum,
                candidate_grid_maximum=candidate_grid_maximum,
                candidate_grid_step=candidate_grid_step,
            ):
                return estimate_federated_matched(
                    request.policy_id,
                    request.calibration,
                    Probability(quantile),
                    grid_minimum=candidate_grid_minimum,
                    grid_maximum=candidate_grid_maximum,
                    grid_step=candidate_grid_step,
                )
            case FederatedFixedPolicy(
                kind=ThresholdPolicyKind.FEDERATED_FIXED, quantile=quantile, fixed_coefficient=fixed_coefficient
            ):
                return estimate_federated_fixed(
                    request.policy_id,
                    request.calibration,
                    Probability(quantile),
                    fixed_coefficient,
                )
            case _:
                raise UnsupportedThresholdPolicyError(f"No estimator for threshold policy kind: {policy.kind.value}")
