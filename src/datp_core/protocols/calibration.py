"""Benign-only calibration declarations."""

from datp_core.domain.enums import (
    ClusterAssignmentAlgorithm,
    ClusterFeatureStandardization,
    ClusterThresholdAggregation,
    FederatedThresholdMethod,
    KMeansInitialization,
)
from datp_core.domain.values import (
    CalibrationSize,
    CoverageTarget,
    GroupCount,
    KMeansInitializationCount,
    KMeansMaximumIterationCount,
    Quantile,
    Ratio,
    Seed,
    ShrinkageWeight,
    SummaryCoefficient,
)

from .models import (
    LOCKED_CLUSTER_GROUP_COUNT,
    LOCKED_CLUSTER_INITIALIZATION_COUNT,
    LOCKED_CLUSTER_MAXIMUM_ITERATIONS,
    LOCKED_CLUSTER_RANDOM_STATE,
    REQUIRED_CLUSTER_FINGERPRINT_FEATURES,
    CalibrationEligibilityProtocol,
    CalibrationSizeProtocol,
    ClusterThresholdProtocol,
    ConformalProtocol,
    FederatedStatisticsProtocol,
    FixedShrinkageProtocol,
    QuantileProtocol,
    SizeAwareShrinkageProtocol,
)

CANONICAL_QUANTILE = Quantile(0.95)
QUANTILE_GRID = tuple(Quantile(value) for value in (0.90, 0.95, 0.975, 0.99))
MINIMUM_BENIGN_SUPPORT = CalibrationSize(100)
CALIBRATION_SIZES = tuple(CalibrationSize(value) for value in (50, 100, 250, 500, 1000, 5000))
FIXED_SHRINKAGE_WEIGHTS = tuple(ShrinkageWeight(value) for value in (0, 0.25, 0.5, 0.75, 1))
CONFORMAL_COVERAGE = CoverageTarget(0.95)
CONFORMAL_SIGNIFICANCE = Ratio(0.05)
SUMMARY_COEFFICIENTS = tuple(SummaryCoefficient(value) for value in (2, 2.5, 3))
CALIBRATION_ELIGIBILITY_PROTOCOL = CalibrationEligibilityProtocol(minimum_support=MINIMUM_BENIGN_SUPPORT)
CALIBRATION_SIZE_PROTOCOL = CalibrationSizeProtocol(sizes=CALIBRATION_SIZES)
SHARED_THRESHOLD_PROTOCOL = QuantileProtocol(
    method=FederatedThresholdMethod.SHARED_THRESHOLD,
    quantile=CANONICAL_QUANTILE,
)
LOCAL_THRESHOLD_PROTOCOL = QuantileProtocol(
    method=FederatedThresholdMethod.LOCAL_THRESHOLD,
    quantile=CANONICAL_QUANTILE,
)
POOLED_SHARED_QUANTILE_PROTOCOL = QuantileProtocol(
    method=FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
    quantile=CANONICAL_QUANTILE,
)
SAMPLE_WEIGHTED_SHARED_THRESHOLD_PROTOCOL = QuantileProtocol(
    method=FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
    quantile=CANONICAL_QUANTILE,
)
FIXED_SHRINKAGE_PROTOCOL = FixedShrinkageProtocol(
    method=FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
    weights=FIXED_SHRINKAGE_WEIGHTS,
)
SIZE_AWARE_SHRINKAGE_PROTOCOL = SizeAwareShrinkageProtocol(
    method=FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
    minimum_support=MINIMUM_BENIGN_SUPPORT,
)
CONFORMAL_PROTOCOL = ConformalProtocol(
    method=FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
    coverage=CONFORMAL_COVERAGE,
    significance=CONFORMAL_SIGNIFICANCE,
)
FEDERATED_STATISTICS_PROTOCOL = FederatedStatisticsProtocol(
    method=FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
    coefficients=SUMMARY_COEFFICIENTS,
)
CLUSTER_THRESHOLD_PROTOCOL = ClusterThresholdProtocol(
    method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
    quantile=CANONICAL_QUANTILE,
    fingerprint_features=REQUIRED_CLUSTER_FINGERPRINT_FEATURES,
    feature_standardization=ClusterFeatureStandardization.STANDARD_SCALER,
    assignment_algorithm=ClusterAssignmentAlgorithm.KMEANS,
    initialization=KMeansInitialization.KMEANS_PLUS_PLUS,
    initialization_count=KMeansInitializationCount(LOCKED_CLUSTER_INITIALIZATION_COUNT),
    maximum_iterations=KMeansMaximumIterationCount(LOCKED_CLUSTER_MAXIMUM_ITERATIONS),
    random_state=Seed(LOCKED_CLUSTER_RANDOM_STATE),
    group_count=GroupCount(LOCKED_CLUSTER_GROUP_COUNT),
    threshold_aggregation=ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS,
)
