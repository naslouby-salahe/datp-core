"""Exhaustive, typed dispatch over `FederatedThresholdMethod`.

No registry dictionary, plugin discovery, or fallback estimator: every federated
threshold method is one explicit `match` arm calling its own construction module.
`CentralizedThresholdMethod` is rejected both structurally (the request only ever
types `method` as `FederatedThresholdMethod`) and by an explicit runtime guard.
"""

from dataclasses import dataclass

from datp_core.domain.enums import CentralizedThresholdMethod, ContractSubject, FederatedThresholdMethod
from datp_core.domain.errors import CapabilityError, LeakageError, ScientificContractError
from datp_core.domain.values import FamilyIdentity, Quantile
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity, PopulationCapabilities
from datp_core.protocols.calibration import (
    CLUSTER_THRESHOLD_PROTOCOL,
    FEDERATED_STATISTICS_PROTOCOL,
    FIXED_SHRINKAGE_PROTOCOL,
)
from datp_core.protocols.models import QuantileProtocol
from datp_core.thresholding.conformal import construct_local_conformal_threshold
from datp_core.thresholding.family import construct_family_threshold
from datp_core.thresholding.federated_benign_statistics import construct_federated_benign_statistics
from datp_core.thresholding.grouped import construct_grouped_threshold
from datp_core.thresholding.local import construct_local_threshold
from datp_core.thresholding.models import (
    ThresholdConstructionResult,
    ThresholdInfeasibilityReason,
    ThresholdUnavailableResult,
)
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores
from datp_core.thresholding.shared import (
    construct_pooled_shared_quantile,
    construct_sample_weighted_shared_threshold,
    construct_shared_threshold,
)
from datp_core.thresholding.shrinkage import construct_fixed_shrinkage, construct_size_aware_shrinkage


def reject_centralized_threshold_method(method: FederatedThresholdMethod | CentralizedThresholdMethod) -> None:
    if isinstance(method, CentralizedThresholdMethod):
        raise LeakageError("centralized threshold methods cannot enter federated dispatch", subject=method)


def validate_population_capability(capabilities: PopulationCapabilities, method: FederatedThresholdMethod) -> None:
    if method not in capabilities.valid_threshold_methods:
        raise CapabilityError(f"{method.value} is not a valid threshold method for this population", subject=method)


def _family_threshold_or_unavailable(
    request: "ThresholdConstructionRequest",
) -> ThresholdConstructionResult:
    if not request.family_by_client:
        return ThresholdUnavailableResult(
            method=FederatedThresholdMethod.FAMILY_THRESHOLD,
            coordinate=request.coordinate,
            reason=ThresholdInfeasibilityReason.FAMILY_TAXONOMY_UNAVAILABLE,
            detail="No family taxonomy was supplied for this population.",
        )
    return construct_family_threshold(request.eligible, request.quantile, request.family_by_client)


def _cluster_threshold_or_unavailable(
    request: "ThresholdConstructionRequest",
) -> ThresholdConstructionResult:
    if len(request.eligible) <= CLUSTER_THRESHOLD_PROTOCOL.group_count.value:
        return ThresholdUnavailableResult(
            method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
            coordinate=request.coordinate,
            reason=ThresholdInfeasibilityReason.GROUP_COUNT_EXCEEDS_ELIGIBLE_POPULATION,
            detail="The eligible population does not exceed the locked cluster group count.",
        )
    protocol = CLUSTER_THRESHOLD_PROTOCOL.model_copy(update={"quantile": request.quantile})
    return construct_grouped_threshold(request.eligible, protocol)


@dataclass(frozen=True, slots=True)
class ThresholdConstructionRequest:
    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    capabilities: PopulationCapabilities
    eligible: tuple[ClientBenignCalibrationScores, ...]
    family_by_client: tuple[tuple[ClientIdentity, FamilyIdentity], ...]

    def __post_init__(self) -> None:
        if not self.eligible:
            raise ScientificContractError(
                "threshold construction requires at least one eligible client", subject=ContractSubject.THRESHOLD
            )
        eligible_clients = tuple(item.client for item in self.eligible)
        if len(set(eligible_clients)) != len(eligible_clients):
            raise ScientificContractError(
                "eligible clients must have unique identities", subject=ContractSubject.CLIENT_IDENTITY
            )
        for item in self.eligible:
            if item.coordinate != self.coordinate:
                raise ScientificContractError(
                    "every eligible entry must carry the request coordinate", subject=ContractSubject.COORDINATE
                )
        family_clients = tuple(entry[0] for entry in self.family_by_client)
        if len(set(family_clients)) != len(family_clients):
            raise ScientificContractError(
                "family-by-client entries must have unique client identities", subject=ContractSubject.CLIENT_IDENTITY
            )


def dispatch_federated_threshold(request: ThresholdConstructionRequest) -> ThresholdConstructionResult:
    reject_centralized_threshold_method(request.method)
    validate_population_capability(request.capabilities, request.method)

    result: ThresholdConstructionResult
    match request.method:
        case FederatedThresholdMethod.SHARED_THRESHOLD:
            result = construct_shared_threshold(
                request.eligible,
                QuantileProtocol(method=FederatedThresholdMethod.SHARED_THRESHOLD, quantile=request.quantile),
            )
        case FederatedThresholdMethod.LOCAL_THRESHOLD:
            result = construct_local_threshold(
                request.eligible,
                QuantileProtocol(method=FederatedThresholdMethod.LOCAL_THRESHOLD, quantile=request.quantile),
            )
        case FederatedThresholdMethod.POOLED_SHARED_QUANTILE:
            result = construct_pooled_shared_quantile(
                request.eligible,
                QuantileProtocol(method=FederatedThresholdMethod.POOLED_SHARED_QUANTILE, quantile=request.quantile),
            )
        case FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD:
            result = construct_sample_weighted_shared_threshold(
                request.eligible,
                QuantileProtocol(
                    method=FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD, quantile=request.quantile
                ),
            )
        case FederatedThresholdMethod.FAMILY_THRESHOLD:
            result = _family_threshold_or_unavailable(request)
        case FederatedThresholdMethod.CLUSTER_THRESHOLD:
            result = _cluster_threshold_or_unavailable(request)
        case FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE:
            result = construct_fixed_shrinkage(request.eligible, FIXED_SHRINKAGE_PROTOCOL, request.quantile)
        case FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE:
            result = construct_size_aware_shrinkage(request.coordinate)
        case FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD:
            result = construct_local_conformal_threshold(request.eligible, request.quantile)
        case FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS:
            result = construct_federated_benign_statistics(
                request.eligible, FEDERATED_STATISTICS_PROTOCOL, request.quantile
            )
    return result
