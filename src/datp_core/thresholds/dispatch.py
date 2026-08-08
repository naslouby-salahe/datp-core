"""Exhaustive typed dispatch over federated threshold methods."""

from dataclasses import dataclass
from typing import assert_never

from datp_core.core.errors import CapabilityError, LeakageError, ScientificContractError
from datp_core.core.identifiers import CentralizedThresholdMethod, ContractSubject, FederatedThresholdMethod
from datp_core.core.numeric import Quantile, RowCount
from datp_core.data.populations.contracts import PopulationCapabilities
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.contracts import (
    FamilyAssignment,
    ThresholdInfeasibilityReason,
    ThresholdUnavailableResult,
)
from datp_core.thresholds.policies.cluster import GroupedThresholdResult, construct_grouped_threshold
from datp_core.thresholds.policies.family import FamilyThresholdResult, construct_family_threshold
from datp_core.thresholds.policies.local import LocalThresholdResult, construct_local_threshold
from datp_core.thresholds.policies.shared import (
    PooledSharedQuantileResult,
    SampleWeightedSharedThresholdResult,
    SharedThresholdResult,
    construct_pooled_shared_quantile,
    construct_sample_weighted_shared_threshold,
    construct_shared_threshold,
)
from datp_core.thresholds.protocols import (
    CLUSTER_MEDIAN_THRESHOLD_PROTOCOL,
    CLUSTER_THRESHOLD_PROTOCOL,
    FEDERATED_STATISTICS_PROTOCOL,
    FIXED_SHRINKAGE_PROTOCOL,
    MINIMUM_BENIGN_SUPPORT,
    CalibrationSupportRule,
    ClusterThresholdAggregation,
    QuantileProtocol,
)
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores
from datp_core.thresholds.variants.conformal import ConformalThresholdResult, construct_local_conformal_threshold
from datp_core.thresholds.variants.federated_statistics import (
    FederatedStatisticsThresholdResult,
    construct_federated_benign_statistics,
)
from datp_core.thresholds.variants.shrinkage import (
    ShrinkageThresholdResult,
    construct_fixed_shrinkage,
    construct_size_aware_shrinkage,
)

type ThresholdConstructionResult = (
    SharedThresholdResult
    | PooledSharedQuantileResult
    | SampleWeightedSharedThresholdResult
    | LocalThresholdResult
    | FamilyThresholdResult
    | GroupedThresholdResult
    | tuple[ShrinkageThresholdResult, ...]
    | ConformalThresholdResult
    | FederatedStatisticsThresholdResult
    | ThresholdUnavailableResult
)


def reject_centralized_threshold_method(method: FederatedThresholdMethod | CentralizedThresholdMethod) -> None:
    if isinstance(method, CentralizedThresholdMethod):
        raise LeakageError(
            "centralized threshold methods cannot enter federated dispatch",
            subject=method,
        )


def validate_population_capability(capabilities: PopulationCapabilities, method: FederatedThresholdMethod) -> None:
    if method not in capabilities.valid_threshold_methods:
        raise CapabilityError(
            f"{method.value} is not a valid threshold method for this population",
            subject=method,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdConstructionRequest:
    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    capabilities: PopulationCapabilities
    eligible: tuple[ClientBenignCalibrationScores, ...]
    family_by_client: tuple[FamilyAssignment, ...]
    support_rule: CalibrationSupportRule
    cluster_threshold_aggregation: ClusterThresholdAggregation | None

    def __post_init__(self) -> None:
        if not self.eligible:
            raise ScientificContractError(
                "threshold construction requires at least one eligible client",
                subject=ContractSubject.THRESHOLD,
            )
        eligible_clients = tuple(item.client for item in self.eligible)
        if len(set(eligible_clients)) != len(eligible_clients):
            raise ScientificContractError(
                "eligible clients must have unique identities",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        for item in self.eligible:
            if item.coordinate != self.coordinate:
                raise ScientificContractError(
                    "every eligible entry must carry the request coordinate",
                    subject=ContractSubject.COORDINATE,
                )
        family_clients = tuple(item.client for item in self.family_by_client)
        if len(set(family_clients)) != len(family_clients):
            raise ScientificContractError(
                "family-by-client entries must have unique client identities",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        if self.method is FederatedThresholdMethod.CLUSTER_THRESHOLD:
            if self.cluster_threshold_aggregation is None:
                raise ScientificContractError(
                    "cluster threshold construction requires an explicit threshold aggregation",
                    subject=ContractSubject.THRESHOLD,
                )
        elif self.cluster_threshold_aggregation is not None:
            raise ScientificContractError(
                "cluster threshold aggregation is valid only for CLUSTER_THRESHOLD",
                subject=ContractSubject.THRESHOLD,
            )


def dispatch_federated_threshold(request: ThresholdConstructionRequest) -> ThresholdConstructionResult:
    reject_centralized_threshold_method(request.method)
    validate_population_capability(request.capabilities, request.method)
    _validate_support(request)
    match request.method:
        case FederatedThresholdMethod.SHARED_THRESHOLD:
            return construct_shared_threshold(
                request.eligible,
                QuantileProtocol(method=FederatedThresholdMethod.SHARED_THRESHOLD, quantile=request.quantile),
            )
        case FederatedThresholdMethod.LOCAL_THRESHOLD:
            return construct_local_threshold(
                request.eligible,
                QuantileProtocol(method=FederatedThresholdMethod.LOCAL_THRESHOLD, quantile=request.quantile),
            )
        case FederatedThresholdMethod.POOLED_SHARED_QUANTILE:
            return construct_pooled_shared_quantile(
                request.eligible,
                QuantileProtocol(method=FederatedThresholdMethod.POOLED_SHARED_QUANTILE, quantile=request.quantile),
            )
        case FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD:
            return construct_sample_weighted_shared_threshold(
                request.eligible,
                QuantileProtocol(
                    method=FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
                    quantile=request.quantile,
                ),
            )
        case FederatedThresholdMethod.FAMILY_THRESHOLD:
            return _family_threshold_or_unavailable(request)
        case FederatedThresholdMethod.CLUSTER_THRESHOLD:
            return _cluster_threshold_or_unavailable(request)
        case FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE:
            return construct_fixed_shrinkage(request.eligible, FIXED_SHRINKAGE_PROTOCOL, request.quantile)
        case FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE:
            return construct_size_aware_shrinkage(request.coordinate)
        case FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD:
            return construct_local_conformal_threshold(request.eligible, request.quantile)
        case FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS:
            return construct_federated_benign_statistics(
                request.eligible,
                FEDERATED_STATISTICS_PROTOCOL,
                request.quantile,
            )
        case _:
            assert_never(request.method)


def _validate_support(request: ThresholdConstructionRequest) -> None:
    match request.support_rule:
        case CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT:
            for item in request.eligible:
                if not MINIMUM_BENIGN_SUPPORT.fits_within(RowCount(len(item.scores))):
                    raise ScientificContractError(
                        "threshold construction rejects clients below the minimum benign calibration support",
                        subject=ContractSubject.CALIBRATION,
                    )
        case CalibrationSupportRule.DECLARED_SIZE_ABLATION:
            return
        case _:
            assert_never(request.support_rule)


def _family_threshold_or_unavailable(request: ThresholdConstructionRequest) -> ThresholdConstructionResult:
    if not request.family_by_client:
        return ThresholdUnavailableResult(
            method=FederatedThresholdMethod.FAMILY_THRESHOLD,
            coordinate=request.coordinate,
            reason=ThresholdInfeasibilityReason.FAMILY_TAXONOMY_UNAVAILABLE,
            detail="No family taxonomy was supplied for this population.",
        )
    return construct_family_threshold(request.eligible, request.quantile, request.family_by_client)


def _cluster_threshold_or_unavailable(request: ThresholdConstructionRequest) -> ThresholdConstructionResult:
    if len(request.eligible) <= CLUSTER_THRESHOLD_PROTOCOL.group_count.value:
        return ThresholdUnavailableResult(
            method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
            coordinate=request.coordinate,
            reason=ThresholdInfeasibilityReason.GROUP_COUNT_EXCEEDS_ELIGIBLE_POPULATION,
            detail="The eligible population does not exceed the locked cluster group count.",
        )
    match request.cluster_threshold_aggregation:
        case ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS:
            base_protocol = CLUSTER_THRESHOLD_PROTOCOL
        case ClusterThresholdAggregation.MEDIAN_OF_ELIGIBLE_LOCAL_THRESHOLDS:
            base_protocol = CLUSTER_MEDIAN_THRESHOLD_PROTOCOL
        case None:
            raise ScientificContractError(
                "cluster threshold construction requires an explicit aggregation",
                subject=ContractSubject.THRESHOLD,
            )
        case _:
            assert_never(request.cluster_threshold_aggregation)
    protocol = base_protocol.model_copy(update={"quantile": request.quantile})
    return construct_grouped_threshold(request.eligible, protocol)
