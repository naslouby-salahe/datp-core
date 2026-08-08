"""Fixed local-global shrinkage and explicitly unavailable size-aware variant."""

from dataclasses import dataclass
from typing import ClassVar

from datp_core.core.errors import ScientificContractError, require_contract
from datp_core.core.identifiers import ContractSubject, FederatedThresholdMethod
from datp_core.core.numeric import Quantile, ShrinkageWeight, ThresholdValue, floats_exactly_equal
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.contracts import (
    LocalQuantile,
    ThresholdAssignment,
    ThresholdInfeasibilityReason,
    ThresholdUnavailableResult,
    mean_local_threshold,
    validate_assignments,
)
from datp_core.thresholds.protocols import FixedShrinkageProtocol
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores, local_quantile, require_eligible_cohort


@dataclass(frozen=True, slots=True)
class ShrinkageAssignment:
    client: ClientIdentity
    local_quantile: LocalQuantile
    shared_threshold: ThresholdValue
    weight: ShrinkageWeight
    threshold: ThresholdValue

    def __post_init__(self) -> None:
        require_contract(
            self.client == self.local_quantile.client,
            "shrinkage assignment client must match the local quantile client",
            ContractSubject.CLIENT_IDENTITY,
        )
        expected = (
            self.weight.value * self.local_quantile.value.value
            + (1.0 - self.weight.value) * self.shared_threshold.value
        )
        require_contract(
            floats_exactly_equal(self.threshold.value, expected),
            "shrinkage threshold must equal the declared convex local-shared combination",
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class ShrinkageThresholdResult:
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    weight: ShrinkageWeight
    shared_threshold: ThresholdValue
    local_quantiles: tuple[LocalQuantile, ...]
    assignments: tuple[ShrinkageAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE

    def __post_init__(self) -> None:
        expected_assignments = tuple(ThresholdAssignment(item.client, item.threshold) for item in self.assignments)
        validate_assignments(
            expected_assignments,
            tuple(
                ThresholdAssignment(
                    local.client,
                    ThresholdValue(
                        self.weight.value * local.value.value + (1.0 - self.weight.value) * self.shared_threshold.value
                    ),
                )
                for local in self.local_quantiles
            ),
            label="shrinkage assignments",
            mismatch_message="shrinkage assignments must match the declared fixed weight curve",
        )


def construct_fixed_shrinkage(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: FixedShrinkageProtocol,
    quantile: Quantile,
) -> tuple[ShrinkageThresholdResult, ...]:
    if protocol.method is not FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE:
        raise ScientificContractError(
            "fixed shrinkage requires the local-global shrinkage protocol", subject=protocol.method
        )
    require_eligible_cohort(eligible, "fixed shrinkage construction")
    local_quantiles = tuple(local_quantile(item, quantile) for item in eligible)
    shared = mean_local_threshold(local_quantiles)
    return tuple(
        ShrinkageThresholdResult(
            coordinate=eligible[0].coordinate,
            quantile=quantile,
            weight=weight,
            shared_threshold=shared,
            local_quantiles=local_quantiles,
            assignments=tuple(
                ShrinkageAssignment(
                    client=local.client,
                    local_quantile=local,
                    shared_threshold=shared,
                    weight=weight,
                    threshold=ThresholdValue(weight.value * local.value.value + (1.0 - weight.value) * shared.value),
                )
                for local in local_quantiles
            ),
        )
        for weight in protocol.weights
    )


def construct_size_aware_shrinkage(coordinate: FederatedTrainingCoordinate) -> ThresholdUnavailableResult:
    return ThresholdUnavailableResult(
        method=FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
        coordinate=coordinate,
        reason=ThresholdInfeasibilityReason.SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED,
        detail=(
            "The roadmap requires lambda(n_k) to be predeclared, but no size-aware function is scientifically locked."
        ),
    )
