"""`LOCAL_GLOBAL_SHRINKAGE` fixed lambda curve, and the `SIZE_AWARE_SHRINKAGE` blocker.

A size-aware shrinkage function `lambda(n_k)` would need to be fixed before
evaluation, bounded in `[0, 1]`, and identical across clients apart from benign
calibration count. No such function is declared anywhere, so
`construct_size_aware_shrinkage` returns typed unavailability rather than
fabricating a formula; every other method here remains independently executable.
"""

from datp_core.domain.enums import ContractSubject, FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Quantile, ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.models import FixedShrinkageProtocol, QuantileProtocol
from datp_core.thresholding.models import (
    ShrinkageAssignment,
    ShrinkageThresholdResult,
    ThresholdInfeasibilityReason,
    ThresholdUnavailableResult,
)
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores
from datp_core.thresholding.shared import construct_shared_threshold

_SIZE_AWARE_SHRINKAGE_BLOCKER_DETAIL = (
    "Size-aware shrinkage requires a pre-declared, bounded, monotone lambda(n_k) "
    "function of benign calibration count, and no such function is declared; "
    "inventing a formula is forbidden, so this method is reported as unavailable "
    "rather than executed."
)


def construct_fixed_shrinkage(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: FixedShrinkageProtocol,
    quantile: Quantile,
) -> ShrinkageThresholdResult:
    """`LOCAL_GLOBAL_SHRINKAGE`: the complete declared curve of `lambda * local + (1 - lambda) * shared`."""
    if not eligible:
        raise ScientificContractError(
            "fixed shrinkage construction requires at least one eligible client",
            subject=ContractSubject.THRESHOLD,
        )
    shared_result = construct_shared_threshold(
        eligible, QuantileProtocol(method=FederatedThresholdMethod.SHARED_THRESHOLD, quantile=quantile)
    )
    shared_value = shared_result.shared_threshold
    local_quantiles = sorted(shared_result.contributing_local_quantiles, key=lambda item: item.client)

    assignments: list[ShrinkageAssignment] = []
    for weight in protocol.weights:
        for local in local_quantiles:
            blended = weight.value * local.value.value + (1 - weight.value) * shared_value.value
            assignments.append(
                ShrinkageAssignment(
                    client=local.client,
                    lambda_weight=weight,
                    local_threshold=local.value,
                    shared_threshold=shared_value,
                    blended_threshold=ThresholdValue(blended),
                )
            )
    return ShrinkageThresholdResult(
        coordinate=eligible[0].coordinate,
        weights=protocol.weights,
        assignments=tuple(assignments),
    )


def construct_size_aware_shrinkage(coordinate: FederatedTrainingCoordinate) -> ThresholdUnavailableResult:
    """`SIZE_AWARE_SHRINKAGE`: typed unavailability; no source-backed `lambda(n_k)` exists."""
    return ThresholdUnavailableResult(
        method=FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
        coordinate=coordinate,
        reason=ThresholdInfeasibilityReason.SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED,
        detail=_SIZE_AWARE_SHRINKAGE_BLOCKER_DETAIL,
    )
