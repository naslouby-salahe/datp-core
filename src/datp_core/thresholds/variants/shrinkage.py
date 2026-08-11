from dataclasses import dataclass
from typing import ClassVar

from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
    require_contract,
)
from datp_core.core.identifiers import ContractSubject, FederatedThresholdMethod, ValidationLabel
from datp_core.core.numeric import CalibrationSize, Quantile, ShrinkageWeight, ThresholdValue, floats_exactly_equal
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.contracts import (
    LocalQuantile,
    ThresholdAssignment,
    mean_local_threshold,
    validate_assignments,
)
from datp_core.thresholds.protocols import FixedShrinkageProtocol, SizeAwareShrinkageProtocol, SizeAwareShrinkageRule
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
            ErrorMessage("shrinkage assignment client must match the local quantile client"),
            ContractSubject.CLIENT_IDENTITY,
        )
        expected = (
            self.weight.value * self.local_quantile.value.value
            + (1.0 - self.weight.value) * self.shared_threshold.value
        )
        require_contract(
            floats_exactly_equal(self.threshold.value, expected),
            ErrorMessage("shrinkage threshold must equal the declared convex local-shared combination"),
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
            label=ValidationLabel("shrinkage assignments"),
            mismatch_message=ErrorMessage("shrinkage assignments must match the declared fixed weight curve"),
        )


@dataclass(frozen=True, slots=True)
class FixedShrinkageCurveResult:
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    points: tuple[ShrinkageThresholdResult, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE

    def __post_init__(self) -> None:
        require_contract(
            bool(self.points),
            ErrorMessage("fixed shrinkage requires at least one predeclared weight point"),
            ContractSubject.THRESHOLD,
        )
        weights = tuple(point.weight for point in self.points)
        require_contract(
            len(frozenset(weights)) == len(weights),
            ErrorMessage("fixed shrinkage curve weights must be unique"),
            ContractSubject.THRESHOLD,
        )
        for point in self.points:
            require_contract(
                point.coordinate == self.coordinate,
                ErrorMessage("every fixed shrinkage point must carry the curve coordinate"),
                ContractSubject.COORDINATE,
            )
            require_contract(
                point.quantile == self.quantile,
                ErrorMessage("every fixed shrinkage point must carry the curve quantile"),
                ContractSubject.THRESHOLD,
            )


def construct_fixed_shrinkage(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: FixedShrinkageProtocol,
    quantile: Quantile,
) -> FixedShrinkageCurveResult:
    if protocol.method is not FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE:
        raise ScientificContractError(
            ErrorMessage("fixed shrinkage requires the local-global shrinkage protocol"), subject=protocol.method
        )
    require_eligible_cohort(eligible, ValidationLabel("fixed shrinkage construction"))
    local_quantiles = tuple(local_quantile(item, quantile) for item in eligible)
    shared = mean_local_threshold(local_quantiles)
    return FixedShrinkageCurveResult(
        coordinate=eligible[0].coordinate,
        quantile=quantile,
        points=tuple(
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
                        threshold=ThresholdValue(
                            weight.value * local.value.value + (1.0 - weight.value) * shared.value
                        ),
                    )
                    for local in local_quantiles
                ),
            )
            for weight in protocol.weights
        ),
    )


@dataclass(frozen=True, slots=True)
class SizeAwareShrinkageAssignment:
    client: ClientIdentity
    local_quantile: LocalQuantile
    used_support: CalibrationSize
    weight: ShrinkageWeight
    shared_threshold: ThresholdValue
    threshold: ThresholdValue

    def __post_init__(self) -> None:
        require_contract(
            self.client == self.local_quantile.client,
            ErrorMessage("size-aware assignment client must match the local quantile client"),
            ContractSubject.CLIENT_IDENTITY,
        )
        require_contract(
            self.used_support.value == self.local_quantile.calibration_count.value,
            ErrorMessage("size-aware assignment support must equal local quantile support"),
            ContractSubject.CALIBRATION,
        )
        expected = (
            self.weight.value * self.local_quantile.value.value
            + (1.0 - self.weight.value) * self.shared_threshold.value
        )
        require_contract(
            floats_exactly_equal(self.threshold.value, expected),
            ErrorMessage("size-aware threshold must equal the declared convex local-shared combination"),
            ContractSubject.THRESHOLD,
        )


@dataclass(frozen=True, slots=True)
class SizeAwareShrinkageThresholdResult:
    coordinate: FederatedTrainingCoordinate
    quantile: Quantile
    protocol: SizeAwareShrinkageProtocol
    shared_threshold: ThresholdValue
    local_quantiles: tuple[LocalQuantile, ...]
    assignments: tuple[SizeAwareShrinkageAssignment, ...]
    method: ClassVar[FederatedThresholdMethod] = FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE

    def __post_init__(self) -> None:
        validate_assignments(
            tuple(ThresholdAssignment(item.client, item.threshold) for item in self.assignments),
            tuple(
                ThresholdAssignment(
                    item.client,
                    ThresholdValue(
                        item.weight.value * item.local_quantile.value.value
                        + (1.0 - item.weight.value) * self.shared_threshold.value
                    ),
                )
                for item in self.assignments
            ),
            label=ValidationLabel("size-aware shrinkage assignments"),
            mismatch_message=ErrorMessage("size-aware assignments must match the locked protocol"),
        )


def size_aware_shrinkage_weight(
    used_support: CalibrationSize,
    protocol: SizeAwareShrinkageProtocol,
) -> ShrinkageWeight:
    if protocol.method is not FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE:
        raise ScientificContractError(
            ErrorMessage("size-aware weight requires the size-aware protocol"), subject=protocol.method
        )
    if protocol.rule is not SizeAwareShrinkageRule.USED_SUPPORT_OVER_USED_PLUS_CANONICAL_MINIMUM:
        raise ScientificContractError(
            ErrorMessage("size-aware weight requires the locked size-aware rule"), subject=protocol.rule
        )
    weight = ShrinkageWeight(used_support.value / (used_support.value + protocol.half_weight_support.value))
    require_contract(
        0.0 <= weight.value <= 1.0,
        ErrorMessage("size-aware shrinkage weight must be bounded in [0, 1]"),
        ContractSubject.THRESHOLD,
    )
    return weight


def construct_size_aware_shrinkage(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    protocol: SizeAwareShrinkageProtocol,
    quantile: Quantile,
) -> SizeAwareShrinkageThresholdResult:
    if protocol.method is not FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE:
        raise ScientificContractError(
            ErrorMessage("size-aware shrinkage requires the size-aware protocol"), subject=protocol.method
        )
    require_eligible_cohort(eligible, ValidationLabel("size-aware shrinkage construction"))
    local_quantiles = tuple(local_quantile(item, quantile) for item in eligible)
    shared = mean_local_threshold(local_quantiles)
    assignments: list[SizeAwareShrinkageAssignment] = []
    for local in local_quantiles:
        used_support = CalibrationSize(local.calibration_count.value)
        weight = size_aware_shrinkage_weight(used_support, protocol)
        assignments.append(
            SizeAwareShrinkageAssignment(
                client=local.client,
                local_quantile=local,
                used_support=used_support,
                weight=weight,
                shared_threshold=shared,
                threshold=ThresholdValue(weight.value * local.value.value + (1.0 - weight.value) * shared.value),
            )
        )
    return SizeAwareShrinkageThresholdResult(
        coordinate=eligible[0].coordinate,
        quantile=quantile,
        protocol=protocol,
        shared_threshold=shared,
        local_quantiles=local_quantiles,
        assignments=tuple(assignments),
    )
