import pytest

from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.core.numeric import CoverageTarget
from datp_core.thresholds.protocols import (
    CALIBRATION_SIZE_PROTOCOL,
    CALIBRATION_SIZES,
    CANONICAL_QUANTILE,
    CLUSTER_THRESHOLD_PROTOCOL,
    CONFORMAL_PROTOCOL,
    FEDERATED_STATISTICS_PROTOCOL,
    FIXED_SHRINKAGE_PROTOCOL,
    LOCAL_THRESHOLD_PROTOCOL,
    QUANTILE_GRID,
    SHARED_THRESHOLD_PROTOCOL,
    ClusterAssignmentAlgorithm,
    ClusterFeatureStandardization,
    ClusterFingerprintFeature,
    ClusterThresholdAggregation,
    ConformalProtocol,
    KMeansInitialization,
)


def test_calibration_grids_are_locked() -> None:
    assert CANONICAL_QUANTILE.value == 0.95
    assert tuple(item.value for item in QUANTILE_GRID) == (0.9, 0.95, 0.975, 0.99)
    assert tuple(item.value for item in CALIBRATION_SIZES) == (50, 100, 250, 500, 1000, 5000)
    assert CALIBRATION_SIZE_PROTOCOL.sizes == CALIBRATION_SIZES
    assert SHARED_THRESHOLD_PROTOCOL.quantile == CANONICAL_QUANTILE
    assert LOCAL_THRESHOLD_PROTOCOL.quantile == CANONICAL_QUANTILE
    assert FIXED_SHRINKAGE_PROTOCOL.weights[0].value == 0
    assert CONFORMAL_PROTOCOL.coverage.value == 0.95
    assert FEDERATED_STATISTICS_PROTOCOL.coefficients[-1].value == 3


def test_conformal_protocol_computes_significance_from_coverage() -> None:
    conformal = ConformalProtocol(
        method=FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
        coverage=CoverageTarget(0.8),
    )
    assert conformal.significance.value == pytest.approx(0.2)


def test_conformal_protocol_serializes_one_authoritative_probability() -> None:
    assert CONFORMAL_PROTOCOL.significance.value == pytest.approx(0.05)
    assert CONFORMAL_PROTOCOL.model_dump(mode="json") == {
        "method": FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD.value,
        "coverage": 0.95,
    }


def test_grouped_threshold_assignment_matches_the_locked_fingerprint_protocol() -> None:
    assert CLUSTER_THRESHOLD_PROTOCOL.method is FederatedThresholdMethod.CLUSTER_THRESHOLD
    assert CLUSTER_THRESHOLD_PROTOCOL.quantile == CANONICAL_QUANTILE
    assert CLUSTER_THRESHOLD_PROTOCOL.fingerprint_features == (
        ClusterFingerprintFeature.BENIGN_ERROR_MEAN,
        ClusterFingerprintFeature.BENIGN_ERROR_STANDARD_DEVIATION,
        ClusterFingerprintFeature.BENIGN_ERROR_SKEWNESS,
        ClusterFingerprintFeature.BENIGN_ERROR_P95,
    )
    assert CLUSTER_THRESHOLD_PROTOCOL.feature_standardization is ClusterFeatureStandardization.STANDARD_SCALER
    assert CLUSTER_THRESHOLD_PROTOCOL.assignment_algorithm is ClusterAssignmentAlgorithm.KMEANS
    assert CLUSTER_THRESHOLD_PROTOCOL.initialization is KMeansInitialization.KMEANS_PLUS_PLUS
    assert CLUSTER_THRESHOLD_PROTOCOL.initialization_count.value == 10
    assert CLUSTER_THRESHOLD_PROTOCOL.maximum_iterations.value == 300
    assert CLUSTER_THRESHOLD_PROTOCOL.random_state.value == 42
    assert CLUSTER_THRESHOLD_PROTOCOL.group_count.value == 3
    assert (
        CLUSTER_THRESHOLD_PROTOCOL.threshold_aggregation
        is ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS
    )
