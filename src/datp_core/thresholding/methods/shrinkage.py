"""Fixed shrinkage curve and size-aware unavailability boundary."""

from dataclasses import dataclass
from typing import ClassVar

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import (
    ContractSubject,
    FederatedThresholdMethod,
)
from datp_core.domain.errors import ScientificContractError, require_contract
from datp_core.domain.values.base import floats_exactly_equal
from datp_core.domain.values.ratios import Quantile, ShrinkageWeight, ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.calibration import FixedShrinkageProtocol, QuantileProtocol
from datp_core.thresholding.identities import (
    ThresholdInfeasibilityReason,
    ThresholdUnavailableResult,
)
from datp_core.thresholding.methods.shared import construct_shared_threshold
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores

_SIZE_AWARE_SHRINKAGE_BLOCKER_DETAIL = (
    "Size-aware shrinkage requires a pre-declared, bounded, monotone lambda(n_k) "
    "function of benign calibration count, and no such function is declared; "
    "inventing a formula is forbidden, so this method is reported as unavailable "
    "rather than executed."
)


@dataclass(frozen=True, slots=True)
class ShrinkageAssignment:
    client: ClientIdentity
    lambda_weight: ShrinkageWeight
    local_threshold: ThresholdValue
    shared_threshold: ThresholdValue
    blended_threshold: ThresholdValue

    def __post_init__(self) -> None:
        expected = (
            self.lambda_weight.value * self.local_threshold.value
            + (1 - self.lambda_weight.value) * self.shared_threshold.value
        )
        require_contract(
            floats_exactly_equal(self.blended_threshold.value, expected),
            "blended threshold must equal lambda * local + (1 - lambda) * shared",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class ShrinkageThresholdResult:
    coordinate: FederatedTrainingCoordinate
    weights: tuple[ShrinkageWeight, ...]
    assignments: tuple[ShrinkageAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE

    def __post_init__(self) -> None:
        require_contract(
            bool(self.weights),
            "shrinkage construction requires at least one declared lambda",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            len(set(self.weights)) == len(self.weights),
            "declared shrinkage weights must be unique",
            ContractSubject.THRESHOLD,
        )
        require_contract(
            bool(self.assignments),
            "shrinkage construction requires at least one client assignment",
            ContractSubject.THRESHOLD,
        )
        declared_weights = set(self.weights)
        for assignment in self.assignments:
            require_contract(
                assignment.lambda_weight in declared_weights,
                "every shrinkage assignment must use a declared lambda weight",
                ContractSubject.THRESHOLD,
            )
        actual_keys = tuple((assignment.client, assignment.lambda_weight) for assignment in self.assignments)
        require_contract(
            len(set(actual_keys)) == len(actual_keys),
            "exactly one shrinkage assignment is required per (client, lambda_weight) pair",
            ContractSubject.THRESHOLD,
        )
        clients = frozenset(assignment.client for assignment in self.assignments)
        for weight in self.weights:
            observed = frozenset(
                assignment.client for assignment in self.assignments if assignment.lambda_weight == weight
            )
            require_contract(
                observed == clients,
                "every declared lambda must be evaluated for exactly the same client set",
                ContractSubject.THRESHOLD,
            )
        require_contract(
            len(self.assignments) == len(clients) * len(self.weights),
            "every declared (client, lambda_weight) combination must exist exactly once",
            ContractSubject.THRESHOLD,
        )


def construct_fixed_shrinkage(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: FixedShrinkageProtocol,
    quantile: Quantile,
) -> ShrinkageThresholdResult:
    if not eligible:
        raise ScientificContractError(
            "fixed shrinkage construction requires at least one eligible client",
            subject=ContractSubject.THRESHOLD,
        )
    shared_result = construct_shared_threshold(
        eligible,
        QuantileProtocol(
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
            quantile=quantile,
        ),
    )
    shared_value = shared_result.shared_threshold
    local_quantiles = sorted(
        shared_result.contributing_local_quantiles,
        key=lambda item: item.client,
    )
    assignments = tuple(
        ShrinkageAssignment(
            client=local.client,
            lambda_weight=weight,
            local_threshold=local.value,
            shared_threshold=shared_value,
            blended_threshold=ThresholdValue(
                weight.value * local.value.value + (1 - weight.value) * shared_value.value
            ),
        )
        for weight in protocol.weights
        for local in local_quantiles
    )
    return ShrinkageThresholdResult(
        coordinate=eligible[0].coordinate,
        weights=protocol.weights,
        assignments=assignments,
    )


def construct_size_aware_shrinkage(
    coordinate: FederatedTrainingCoordinate,
) -> ThresholdUnavailableResult:
    return ThresholdUnavailableResult(
        method=FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
        coordinate=coordinate,
        reason=(ThresholdInfeasibilityReason.SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED),
        detail=_SIZE_AWARE_SHRINKAGE_BLOCKER_DETAIL,
    )
