"""Typed benign-only calibration eligibility and subsampling records."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import CalibrationSize, Checksum, ReplicateIndex, RowCount, ScoreValue, Seed
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity


def _raise_first_violation(
    *, requirements: tuple[tuple[bool, str], ...], subject: ContractSubject
) -> None:
    for satisfied, message in requirements:
        if not satisfied:
            raise ScientificContractError(message, subject=subject)


class CalibrationUnavailableReason(StrEnum):
    """Closed reasons a calibration operation is unavailable for a client."""

    INSUFFICIENT_BENIGN_SUPPORT = "insufficient_benign_support"
    CALIBRATION_SIZE_EXCEEDS_SOURCE = "calibration_size_exceeds_source"


class EligibilityStatus(StrEnum):
    CANDIDATE = "candidate"
    ELIGIBLE = "eligible"
    EXCLUDED = "excluded"


@dataclass(frozen=True, slots=True)
class CalibrationSupport:
    """Benign-only calibration support for one client, bound to one frozen score artifact."""

    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    benign_calibration_count: RowCount
    calibration_score_set_checksum: Checksum


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    """The single, immutable eligibility decision for one client, fixed before evaluation."""

    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    benign_calibration_count: RowCount
    minimum_support: CalibrationSize
    status: EligibilityStatus
    reason: CalibrationUnavailableReason | None

    def __post_init__(self) -> None:
        meets_minimum = self.benign_calibration_count >= self.minimum_support
        is_eligible = self.status is EligibilityStatus.ELIGIBLE
        is_excluded = self.status is EligibilityStatus.EXCLUDED
        _raise_first_violation(
            requirements=(
                (
                    not is_eligible or meets_minimum,
                    "eligible status requires benign calibration count to meet the minimum support",
                ),
                (not is_eligible or self.reason is None, "eligible clients cannot carry an unavailability reason"),
                (not is_excluded or self.reason is not None, "excluded clients require a typed unavailability reason"),
            ),
            subject=ContractSubject.CALIBRATION,
        )

    @property
    def is_eligible(self) -> bool:
        return self.status is EligibilityStatus.ELIGIBLE


@dataclass(frozen=True, slots=True)
class CalibrationSampleReference:
    """A reference to one immutable benign calibration score row; never a copy of it."""

    client: ClientIdentity
    stable_row_id: str
    score: ScoreValue

    def __post_init__(self) -> None:
        if not self.stable_row_id:
            raise ScientificContractError(
                "a calibration sample reference requires a stable source-row identity",
                subject=ContractSubject.CALIBRATION,
            )


@dataclass(frozen=True, slots=True)
class CalibrationSubsample:
    """One deterministic, without-replacement subsample of a declared calibration size."""

    client: ClientIdentity
    size: CalibrationSize
    replicate_index: ReplicateIndex
    references: tuple[CalibrationSampleReference, ...]

    def __post_init__(self) -> None:
        if len(self.references) != self.size.value:
            raise ScientificContractError(
                "subsample reference count must equal the declared calibration size",
                subject=ContractSubject.CALIBRATION,
            )
        stable_row_ids = tuple(reference.stable_row_id for reference in self.references)
        if len(set(stable_row_ids)) != len(stable_row_ids):
            raise ScientificContractError(
                "subsample references must be drawn without replacement",
                subject=ContractSubject.CALIBRATION,
            )

    @property
    def stable_row_id_set(self) -> frozenset[str]:
        return frozenset(reference.stable_row_id for reference in self.references)


@dataclass(frozen=True, slots=True)
class CalibrationReplicateManifest:
    """One deterministic subsampling replicate for a client, nested within a training seed."""

    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    training_seed: Seed
    replicate_index: ReplicateIndex
    full_calibration_count: RowCount
    subsamples: tuple[CalibrationSubsample, ...]
    unavailable_sizes: tuple[CalibrationSize, ...]
    unavailable_reason: CalibrationUnavailableReason | None

    def __post_init__(self) -> None:
        if bool(self.unavailable_sizes) != (self.unavailable_reason is not None):
            raise ScientificContractError(
                "unavailable sizes require exactly one typed reason, and vice versa",
                subject=ContractSubject.CALIBRATION,
            )
        _require_ascending_subsample_order(self.subsamples)
        _require_subsamples_belong_to_client(self.subsamples, self.client)
        _require_nested_subsamples(self.subsamples)


def _require_ascending_subsample_order(subsamples: tuple[CalibrationSubsample, ...]) -> None:
    ordered_sizes = tuple(subsample.size.value for subsample in subsamples)
    if ordered_sizes != tuple(sorted(ordered_sizes)):
        raise ScientificContractError(
            "subsamples must be ordered by ascending calibration size",
            subject=ContractSubject.CALIBRATION,
        )


def _require_subsamples_belong_to_client(subsamples: tuple[CalibrationSubsample, ...], client: ClientIdentity) -> None:
    for subsample in subsamples:
        if any(reference.client != client for reference in subsample.references):
            raise ScientificContractError(
                "subsample references must belong to the manifest client",
                subject=ContractSubject.CALIBRATION,
            )


def _require_nested_subsamples(subsamples: tuple[CalibrationSubsample, ...]) -> None:
    ordered = sorted(subsamples, key=lambda subsample: subsample.size.value)
    for smaller, larger in zip(ordered, ordered[1:], strict=False):
        if not smaller.stable_row_id_set.issubset(larger.stable_row_id_set):
            raise ScientificContractError(
                "a smaller calibration subsample must be a subset of the same replicate's larger subsample",
                subject=ContractSubject.CALIBRATION,
            )
