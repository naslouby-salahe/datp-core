"""Benign-only threshold protocols, assignments, and validation contracts."""

from dataclasses import dataclass
from enum import StrEnum
from statistics import fmean
from typing import ClassVar, Literal, Protocol, runtime_checkable

from pydantic import model_validator

from datp_core.artifacts.provenance import Checksum
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ScientificContractError, UnresolvedScientificValueError, require_contract
from datp_core.core.identifiers import (
    AvailabilityStatus,
    CentralizedThresholdMethod,
    ContractSubject,
    FamilyIdentity,
    FederatedThresholdMethod,
    QuantileInterpolationSemantics,
)
from datp_core.core.numeric import (
    CalibrationSize,
    CoverageTarget,
    GroupCount,
    KMeansInitializationCount,
    KMeansMaximumIterationCount,
    NormalizedWeight,
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    Quantile,
    Ratio,
    RowCount,
    Seed,
    ShrinkageWeight,
    SubsampleReplicateCount,
    SummaryCoefficient,
    ThresholdValue,
    floats_absolutely_close,
    floats_exactly_equal,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate


class ThresholdInfeasibilityReason(StrEnum):
    SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED = "size_aware_shrinkage_function_unresolved"
    FAMILY_TAXONOMY_UNAVAILABLE = "family_taxonomy_unavailable"
    GROUP_COUNT_EXCEEDS_ELIGIBLE_POPULATION = "group_count_exceeds_eligible_population"


@dataclass(frozen=True, slots=True)
class ThresholdUnavailableResult:
    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    reason: ThresholdInfeasibilityReason
    detail: str

    def __post_init__(self) -> None:
        require_contract(
            bool(self.detail.strip()),
            "an unavailable threshold result requires a human-readable detail",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class ThresholdDiagnostic:
    quantile_interpolation: QuantileInterpolationSemantics | None
    score_set_checksum: Checksum
    calibration_manifest_checksum: Checksum
    tie_count: RowCount
    availability: AvailabilityStatus


@dataclass(frozen=True, slots=True)
class LocalQuantile:
    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    value: ThresholdValue
    calibration_count: RowCount
    diagnostic: ThresholdDiagnostic

    def __post_init__(self) -> None:
        require_contract(
            self.calibration_count.value >= 1,
            "a local quantile requires at least one benign calibration score",
            ContractSubject.CALIBRATION,
        )


@dataclass(frozen=True, slots=True)
class ThresholdAssignment:
    client: ClientIdentity
    threshold: ThresholdValue


@dataclass(frozen=True, slots=True)
class FamilyAssignment:
    client: ClientIdentity
    family: FamilyIdentity


@runtime_checkable
class ThresholdAssignmentLike(Protocol):
    @property
    def client(self) -> ClientIdentity: ...

    @property
    def threshold(self) -> ThresholdValue: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdAssignmentSet[AssignmentT: ThresholdAssignmentLike]:
    assignments: tuple[AssignmentT, ...]

    def __post_init__(self) -> None:
        if not self.assignments:
            raise ScientificContractError(
                "threshold assignment set requires at least one assignment",
                subject=ContractSubject.THRESHOLD,
            )
        clients = tuple(item.client for item in self.assignments)
        if len(frozenset(clients)) != len(clients):
            raise ScientificContractError(
                "threshold assignment clients must be unique",
                subject=ContractSubject.CLIENT_IDENTITY,
            )

    @property
    def clients(self) -> tuple[ClientIdentity, ...]:
        return tuple(item.client for item in self.assignments)


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdConstructionContext:
    coordinate: FederatedTrainingCoordinate
    calibration_manifest_checksum: Checksum
    score_set_checksum: Checksum
    quantile: Quantile


@runtime_checkable
class FederatedThresholdResult(Protocol):
    coordinate: FederatedTrainingCoordinate
    assignments: tuple[ThresholdAssignmentLike, ...]
    method: ClassVar[FederatedThresholdMethod]


def mean_local_threshold(quantiles: tuple[LocalQuantile, ...]) -> ThresholdValue:
    if not quantiles:
        raise ScientificContractError("mean local threshold requires local quantiles", subject=ContractSubject.THRESHOLD)
    return ThresholdValue(fmean(item.value.value for item in quantiles))


def median_local_threshold(quantiles: tuple[LocalQuantile, ...]) -> ThresholdValue:
    ordered = tuple(sorted(item.value.value for item in quantiles))
    if not ordered:
        raise ScientificContractError("median local threshold requires local quantiles", subject=ContractSubject.THRESHOLD)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ThresholdValue(ordered[midpoint])
    return ThresholdValue((ordered[midpoint - 1] + ordered[midpoint]) / 2.0)


def require_unique_clients(clients: tuple[ClientIdentity, ...], label: str) -> None:
    require_contract(
        len(frozenset(clients)) == len(clients),
        f"{label} must have unique client identities",
        ContractSubject.CLIENT_IDENTITY,
    )


def validate_local_quantiles(
    quantiles: tuple[LocalQuantile, ...],
    coordinate: FederatedTrainingCoordinate,
    *,
    method: FederatedThresholdMethod,
) -> None:
    if method is FederatedThresholdMethod.LOCAL_THRESHOLD:
        message = "local threshold construction requires at least one eligible client"
        label = "local quantiles"
    elif method in {
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
    }:
        message = "shared threshold construction requires at least one contributing local quantile"
        label = "contributing local quantiles"
    else:
        raise ScientificContractError(
            f"local quantile validation does not support threshold method {method}",
            subject=ContractSubject.THRESHOLD,
        )
    require_contract(bool(quantiles), message, ContractSubject.THRESHOLD)
    require_unique_clients(tuple(item.client for item in quantiles), label)
    for item in quantiles:
        require_contract(
            item.coordinate == coordinate,
            "every nested quantile must carry the containing result coordinate",
            ContractSubject.COORDINATE,
        )


def validate_assignments(
    assignments: tuple[ThresholdAssignment, ...],
    expected_assignments: tuple[ThresholdAssignment, ...],
    *,
    label: str,
    mismatch_message: str,
) -> None:
    assigned_clients = tuple(item.client for item in assignments)
    expected_clients = tuple(item.client for item in expected_assignments)
    require_unique_clients(assigned_clients, label)
    require_unique_clients(expected_clients, "expected clients")
    require_contract(
        frozenset(assigned_clients) == frozenset(expected_clients),
        "threshold assignments must cover exactly the contributing client set",
        ContractSubject.CLIENT_IDENTITY,
    )
    require_contract(
        frozenset(assignments) == frozenset(expected_assignments),
        mismatch_message,
        ContractSubject.THRESHOLD,
    )


def validate_normalized_weights(
    weights: tuple[NormalizedWeight, ...],
    quantiles: tuple[LocalQuantile, ...],
) -> None:
    require_contract(
        len(weights) == len(quantiles),
        "one normalized weight is required per contributing local quantile",
        ContractSubject.THRESHOLD,
    )
    require_contract(
        floats_absolutely_close(
            sum(weight.value for weight in weights),
            1.0,
            NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value,
        ),
        "normalized weights must sum to one",
        ContractSubject.THRESHOLD,
    )


def validate_group_membership(
    members: tuple[ClientIdentity, ...],
    contributing_local_quantiles: tuple[LocalQuantile, ...],
    group_threshold: ThresholdValue,
    *,
    members_label: str,
    match_message: str,
    threshold_message: str,
    expected_group_threshold: ThresholdValue | None = None,
) -> None:
    require_unique_clients(members, members_label)
    quantile_clients = tuple(item.client for item in contributing_local_quantiles)
    require_unique_clients(quantile_clients, "contributing local quantiles")
    require_contract(
        frozenset(quantile_clients) == frozenset(members),
        match_message,
        ContractSubject.CLIENT_IDENTITY,
    )
    expected = expected_group_threshold or mean_local_threshold(contributing_local_quantiles)
    require_contract(
        floats_exactly_equal(group_threshold.value, expected.value),
        threshold_message,
        ContractSubject.THRESHOLD,
    )


def validate_client_partition(
    eligible_clients: tuple[ClientIdentity, ...],
    assigned_clients: tuple[ClientIdentity, ...],
    unavailable_clients: tuple[ClientIdentity, ...],
) -> None:
    require_unique_clients(eligible_clients, "eligible clients")
    require_unique_clients(assigned_clients, "assigned clients")
    require_unique_clients(unavailable_clients, "unavailable clients")
    assigned_set = frozenset(assigned_clients)
    unavailable_set = frozenset(unavailable_clients)
    require_contract(
        not assigned_set.intersection(unavailable_set),
        "a client cannot be both assigned and unavailable",
        ContractSubject.CLIENT_IDENTITY,
    )
    require_contract(
        assigned_set.union(unavailable_set) == frozenset(eligible_clients),
        "assigned and unavailable clients must exactly cover the eligible client set",
        ContractSubject.CLIENT_IDENTITY,
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
        if self.sizes != tuple(sorted(self.sizes, key=lambda item: item.value)):
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
            (self.fingerprint_features == REQUIRED_CLUSTER_FINGERPRINT_FEATURES, "cluster fingerprint must use the locked four features in order"),
            (self.feature_standardization is ClusterFeatureStandardization.STANDARD_SCALER, "cluster fingerprint standardization must be StandardScaler"),
            (self.assignment_algorithm is ClusterAssignmentAlgorithm.KMEANS, "cluster assignment must be k-means"),
            (self.initialization is KMeansInitialization.KMEANS_PLUS_PLUS, "cluster initialization must be k-means++"),
            (self.initialization_count == LOCKED_CLUSTER_INITIALIZATION_COUNT, "cluster n_init must match the locked count"),
            (self.maximum_iterations == LOCKED_CLUSTER_MAXIMUM_ITERATIONS, "cluster max_iter must match the locked count"),
            (self.random_state == LOCKED_CLUSTER_RANDOM_STATE, "cluster random_state must match the locked seed"),
            (self.group_count == LOCKED_CLUSTER_GROUP_COUNT, "cluster group count must match the locked group count"),
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
CALIBRATION_SIZES = tuple(CalibrationSize(value) for value in (50, 100, 250, 500, 1000, 5000))
FIXED_SHRINKAGE_WEIGHTS = tuple(ShrinkageWeight(value) for value in (0, 0.25, 0.5, 0.75, 1))
CONFORMAL_COVERAGE = CoverageTarget(0.95)
SUMMARY_COEFFICIENTS = tuple(SummaryCoefficient(value) for value in (2, 2.5, 3))
CALIBRATION_ELIGIBILITY_PROTOCOL = CalibrationEligibilityProtocol(minimum_support=MINIMUM_BENIGN_SUPPORT)
CALIBRATION_SIZE_PROTOCOL = CalibrationSizeProtocol(sizes=CALIBRATION_SIZES)
SHARED_THRESHOLD_PROTOCOL = QuantileProtocol(method=FederatedThresholdMethod.SHARED_THRESHOLD, quantile=CANONICAL_QUANTILE)
LOCAL_THRESHOLD_PROTOCOL = QuantileProtocol(method=FederatedThresholdMethod.LOCAL_THRESHOLD, quantile=CANONICAL_QUANTILE)
POOLED_SHARED_QUANTILE_PROTOCOL = QuantileProtocol(method=FederatedThresholdMethod.POOLED_SHARED_QUANTILE, quantile=CANONICAL_QUANTILE)
SAMPLE_WEIGHTED_SHARED_THRESHOLD_PROTOCOL = QuantileProtocol(method=FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD, quantile=CANONICAL_QUANTILE)
FIXED_SHRINKAGE_PROTOCOL = FixedShrinkageProtocol(method=FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE, weights=FIXED_SHRINKAGE_WEIGHTS)
SIZE_AWARE_SHRINKAGE_PROTOCOL = SizeAwareShrinkageProtocol(method=FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE, minimum_support=MINIMUM_BENIGN_SUPPORT)
CONFORMAL_PROTOCOL = ConformalProtocol(method=FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD, coverage=CONFORMAL_COVERAGE)
FEDERATED_STATISTICS_PROTOCOL = FederatedStatisticsProtocol(method=FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS, coefficients=SUMMARY_COEFFICIENTS)
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
    raise UnresolvedScientificValueError(
        "the master roadmap requires multiple deterministic calibration subsampling replicates but does not declare their count",
        subject=ContractSubject.CALIBRATION,
    )
