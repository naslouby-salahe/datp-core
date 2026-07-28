"""Benign-only calibration declarations."""

from datp_core.domain.enums import (
    ClusterAssignmentAlgorithm,
    ClusterFeatureStandardization,
    ClusterFingerprintFeature,
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

from .models import ClusterThresholdProtocol

CANONICAL_QUANTILE = Quantile(0.95)
QUANTILE_GRID = tuple(Quantile(value) for value in (0.90, 0.95, 0.975, 0.99))
MINIMUM_BENIGN_SUPPORT = CalibrationSize(100)
CALIBRATION_SIZES = tuple(CalibrationSize(value) for value in (50, 100, 250, 500, 1000, 5000))
FIXED_SHRINKAGE_WEIGHTS = tuple(ShrinkageWeight(value) for value in (0, 0.25, 0.5, 0.75, 1))
CONFORMAL_COVERAGE = CoverageTarget(0.95)
CONFORMAL_SIGNIFICANCE = Ratio(0.05)
SUMMARY_COEFFICIENTS = tuple(SummaryCoefficient(value) for value in (2, 2.5, 3))
CLUSTER_THRESHOLD_PROTOCOL = ClusterThresholdProtocol(
    method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
    quantile=CANONICAL_QUANTILE,
    fingerprint_features=tuple(ClusterFingerprintFeature),
    feature_standardization=ClusterFeatureStandardization.STANDARD_SCALER,
    assignment_algorithm=ClusterAssignmentAlgorithm.KMEANS,
    initialization=KMeansInitialization.KMEANS_PLUS_PLUS,
    initialization_count=KMeansInitializationCount(10),
    maximum_iterations=KMeansMaximumIterationCount(300),
    random_state=Seed(42),
    group_count=GroupCount(3),
    threshold_aggregation=ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS,
)
