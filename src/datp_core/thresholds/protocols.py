from enum import StrEnum
from typing import Literal

from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import CentralizedThresholdMethod, FederatedThresholdMethod
from datp_core.core.numeric import (
    CalibrationSize,
    CoverageTarget,
    GroupCount,
    KMeansInitializationCount,
    KMeansMaximumIterationCount,
    Quantile,
    Ratio,
    Seed,
    ShrinkageWeight,
    SubsampleReplicateCount,
    SummaryCoefficient,
)


class ClusterFingerprintFeature(StrEnum):
    BENIGN_ERROR_MEAN = "benign_error_mean"
    BENIGN_ERROR_STANDARD_DEVIATION = "benign_error_standard_deviation"
    BENIGN_ERROR_SKEWNESS = "benign_error_skewness"
    BENIGN_ERROR_P95 = "benign_error_p95"


class ClusterFeatureStandardization(StrEnum):
    STANDARD_SCALER = "standard_scaler"


class ClusterAssignmentAlgorithm(StrEnum):
    KMEANS = "kmeans"


class KMeansInitialization(StrEnum):
    KMEANS_PLUS_PLUS = "kmeans_plus_plus"


class ClusterThresholdAggregation(StrEnum):
    ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS = "arithmetic_mean_of_eligible_local_thresholds"
    MEDIAN_OF_ELIGIBLE_LOCAL_THRESHOLDS = "median_of_eligible_local_thresholds"


class CalibrationSupportRule(StrEnum):
    CANONICAL_MINIMUM_SUPPORT = "canonical_minimum_support"
    DECLARED_SIZE_ABLATION = "declared_size_ablation"


class CalibrationSizeClassification(StrEnum):
    SAMPLE_STARVED_DIAGNOSTIC = "sample_starved_diagnostic"
    FEASIBLE_ABLATION_SIZE = "feasible_ablation_size"


REQUIRED_CLUSTER_FINGERPRINT_FEATURES = (
    ClusterFingerprintFeature.BENIGN_ERROR_MEAN,
    ClusterFingerprintFeature.BENIGN_ERROR_STANDARD_DEVIATION,
    ClusterFingerprintFeature.BENIGN_ERROR_SKEWNESS,
    ClusterFingerprintFeature.BENIGN_ERROR_P95,
)
LOCKED_CLUSTER_INITIALIZATION_COUNT = KMeansInitializationCount(10)
LOCKED_CLUSTER_MAXIMUM_ITERATIONS = KMeansMaximumIterationCount(300)
LOCKED_CLUSTER_RANDOM_STATE = Seed(42)
LOCKED_CLUSTER_GROUP_COUNT = GroupCount(3)


class CentralizedQuantileProtocol(StrictModel):
    method: Literal[CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE]
    quantile: Quantile


class CalibrationEligibilityProtocol(StrictModel):
    minimum_support: CalibrationSize


class QuantileProtocol(StrictModel):
    method: Literal[
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
    ]
    quantile: Quantile


class CalibrationSizeProtocol(StrictModel):
    sizes: tuple[CalibrationSize, ...]

    @model_validator(mode="after")
    def validate_sizes(self) -> "CalibrationSizeProtocol":
        if not self.sizes:
            raise ValueError("calibration-size protocol requires at least one size")
        if len(self.sizes) != len(frozenset(self.sizes)):
            raise ValueError("calibration-size protocol sizes must be unique")
        ordered = tuple(sorted(self.sizes, key=lambda item: item.value))
        if self.sizes != ordered:
            raise ValueError("calibration-size protocol sizes must be ascending")
        return self


class FixedShrinkageProtocol(StrictModel):
    method: Literal[FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE]
    weights: tuple[ShrinkageWeight, ...]


class SizeAwareShrinkageProtocol(StrictModel):
    method: Literal[FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE]
    minimum_support: CalibrationSize


class ConformalProtocol(StrictModel):
    method: Literal[FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD]
    coverage: CoverageTarget

    @property
    def significance(self) -> Ratio:
        return self.coverage.significance


class FederatedStatisticsProtocol(StrictModel):
    method: Literal[FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS]
    coefficients: tuple[SummaryCoefficient, ...]


class ClusterThresholdProtocol(StrictModel):
    method: Literal[FederatedThresholdMethod.CLUSTER_THRESHOLD]
    quantile: Quantile
    fingerprint_features: tuple[ClusterFingerprintFeature, ...]
    feature_standardization: ClusterFeatureStandardization
    assignment_algorithm: ClusterAssignmentAlgorithm
    initialization: KMeansInitialization
    initialization_count: KMeansInitializationCount
    maximum_iterations: KMeansMaximumIterationCount
    random_state: Seed
    group_count: GroupCount
    threshold_aggregation: ClusterThresholdAggregation

    @model_validator(mode="after")
    def validate_fingerprint_features(self) -> "ClusterThresholdProtocol":
        requirements = (
            (
                self.fingerprint_features == REQUIRED_CLUSTER_FINGERPRINT_FEATURES,
                "cluster fingerprint must contain mean, standard deviation, skewness, and p95 "
                "exactly once in locked order",
            ),
            (
                self.feature_standardization is ClusterFeatureStandardization.STANDARD_SCALER,
                "cluster fingerprint standardization must be StandardScaler",
            ),
            (self.assignment_algorithm is ClusterAssignmentAlgorithm.KMEANS, "cluster assignment must be k-means"),
            (
                self.initialization is KMeansInitialization.KMEANS_PLUS_PLUS,
                "cluster initialization must be k-means++",
            ),
            (
                self.initialization_count == LOCKED_CLUSTER_INITIALIZATION_COUNT,
                "cluster n_init must match the locked initialization count",
            ),
            (
                self.maximum_iterations == LOCKED_CLUSTER_MAXIMUM_ITERATIONS,
                "cluster max_iter must match the locked maximum iteration count",
            ),
            (
                self.random_state == LOCKED_CLUSTER_RANDOM_STATE,
                "cluster random_state must match the locked seed",
            ),
            (
                self.group_count == LOCKED_CLUSTER_GROUP_COUNT,
                "cluster group count must match the locked group count",
            ),
            (
                self.threshold_aggregation
                in {
                    ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS,
                    ClusterThresholdAggregation.MEDIAN_OF_ELIGIBLE_LOCAL_THRESHOLDS,
                },
                "cluster thresholds must aggregate eligible local thresholds by locked mean or median",
            ),
        )
        for satisfied, message in requirements:
            if not satisfied:
                raise ValueError(message)
        return self


CANONICAL_QUANTILE = Quantile(0.95)
QUANTILE_GRID = tuple(Quantile(value) for value in (0.90, 0.95, 0.975, 0.99))
MINIMUM_BENIGN_SUPPORT = CalibrationSize(100)

LOCKED_CALIBRATION_SUBSAMPLE_REPLICATE_COUNT = SubsampleReplicateCount(10)
CALIBRATION_SIZES = tuple(CalibrationSize(value) for value in (50, 100, 250, 500, 1000, 5000))
SAMPLE_STARVED_CALIBRATION_SIZE = CalibrationSize(50)
FIXED_SHRINKAGE_WEIGHTS = tuple(ShrinkageWeight(value) for value in (0, 0.25, 0.5, 0.75, 1))
CONFORMAL_COVERAGE = CoverageTarget(0.95)
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
    initialization_count=LOCKED_CLUSTER_INITIALIZATION_COUNT,
    maximum_iterations=LOCKED_CLUSTER_MAXIMUM_ITERATIONS,
    random_state=LOCKED_CLUSTER_RANDOM_STATE,
    group_count=LOCKED_CLUSTER_GROUP_COUNT,
    threshold_aggregation=ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS,
)
CLUSTER_MEDIAN_THRESHOLD_PROTOCOL = ClusterThresholdProtocol(
    method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
    quantile=CANONICAL_QUANTILE,
    fingerprint_features=REQUIRED_CLUSTER_FINGERPRINT_FEATURES,
    feature_standardization=ClusterFeatureStandardization.STANDARD_SCALER,
    assignment_algorithm=ClusterAssignmentAlgorithm.KMEANS,
    initialization=KMeansInitialization.KMEANS_PLUS_PLUS,
    initialization_count=LOCKED_CLUSTER_INITIALIZATION_COUNT,
    maximum_iterations=LOCKED_CLUSTER_MAXIMUM_ITERATIONS,
    random_state=LOCKED_CLUSTER_RANDOM_STATE,
    group_count=LOCKED_CLUSTER_GROUP_COUNT,
    threshold_aggregation=ClusterThresholdAggregation.MEDIAN_OF_ELIGIBLE_LOCAL_THRESHOLDS,
)


def require_calibration_subsample_replicate_count() -> SubsampleReplicateCount:
    return LOCKED_CALIBRATION_SUBSAMPLE_REPLICATE_COUNT


def classify_calibration_size(size: CalibrationSize) -> CalibrationSizeClassification:
    if size == SAMPLE_STARVED_CALIBRATION_SIZE:
        return CalibrationSizeClassification.SAMPLE_STARVED_DIAGNOSTIC
    return CalibrationSizeClassification.FEASIBLE_ABLATION_SIZE
