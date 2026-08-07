from dataclasses import dataclass
from enum import StrEnum

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError, require_contract
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import CalibrationSize, ReplicateIndex, RowCount, Seed
from datp_core.domain.values.identifiers import StableRowId
from datp_core.domain.values.ratios import ScoreValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate


class CalibrationUnavailableReason(StrEnum):
    INSUFFICIENT_BENIGN_SUPPORT = "insufficient_benign_support"
    CALIBRATION_SIZE_EXCEEDS_SOURCE = "calibration_size_exceeds_source"


class EligibilityStatus(StrEnum):
    CANDIDATE = "candidate"
    ELIGIBLE = "eligible"
    EXCLUDED = "excluded"


@dataclass(frozen=True, slots=True)
class CalibrationSupport:
    client: ClientIdentity
    coordinate: FederatedTrainingCoordinate
    benign_calibration_count: RowCount
    calibration_score_set_checksum: Checksum


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    support: CalibrationSupport
    minimum_support: CalibrationSize
    status: EligibilityStatus
    reason: CalibrationUnavailableReason | None

    def __post_init__(self) -> None:
        is_eligible = self.status is EligibilityStatus.ELIGIBLE

        if is_eligible:
            require_contract(
                self.minimum_support.fits_within(self.support.benign_calibration_count),
                "eligible status requires benign calibration count to meet the minimum support",
                ContractSubject.CALIBRATION,
            )
            require_contract(
                self.reason is None,
                "eligible clients cannot carry an unavailability reason",
                ContractSubject.CALIBRATION,
            )
        elif self.status is EligibilityStatus.EXCLUDED:
            require_contract(
                self.reason is not None,
                "excluded clients require a typed unavailability reason",
                ContractSubject.CALIBRATION,
            )

    @property
    def is_eligible(self) -> bool:
        return self.status is EligibilityStatus.ELIGIBLE


@dataclass(frozen=True, slots=True)
class CalibrationSampleReference:
    client: ClientIdentity
    stable_row_id: StableRowId
    score: ScoreValue

    def __post_init__(self) -> None:
        if not self.stable_row_id:
            raise ScientificContractError(
                "a calibration sample reference requires a stable source-row identity",
                subject=ContractSubject.CALIBRATION,
            )


@dataclass(frozen=True, slots=True)
class CalibrationSubsample:
    size: CalibrationSize
    replicate_index: ReplicateIndex
    references: tuple[CalibrationSampleReference, ...]

    def __post_init__(self) -> None:
        if len(self.references) != self.size.value:
            raise ScientificContractError(
                "subsample reference count must equal the declared calibration size",
                subject=ContractSubject.CALIBRATION,
            )

        if not self.references:
            return

        first_client = self.references[0].client
        seen_ids = set()

        for ref in self.references:
            if ref.client != first_client:
                raise ScientificContractError(
                    "subsample references must belong to exactly one client",
                    subject=ContractSubject.CALIBRATION,
                )
            if ref.stable_row_id in seen_ids:
                raise ScientificContractError(
                    "subsample references must be drawn without replacement",
                    subject=ContractSubject.CALIBRATION,
                )
            seen_ids.add(ref.stable_row_id)

    @property
    def client(self) -> ClientIdentity:
        return self.references[0].client

    @property
    def stable_row_id_set(self) -> frozenset[StableRowId]:
        return frozenset(reference.stable_row_id for reference in self.references)


@dataclass(frozen=True, slots=True)
class CalibrationReplicateManifest:
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

        if not self.subsamples:
            return

        _require_ascending_subsample_order(self.subsamples)
        _require_subsamples_belong_to_client(self.subsamples, self.client)
        _require_nested_subsamples(self.subsamples)


def _require_ascending_subsample_order(subsamples: tuple[CalibrationSubsample, ...]) -> None:
    if any(a.size.value > b.size.value for a, b in zip(subsamples, subsamples[1:], strict=False)):
        raise ScientificContractError(
            "subsamples must be ordered by ascending calibration size",
            subject=ContractSubject.CALIBRATION,
        )


def _require_subsamples_belong_to_client(subsamples: tuple[CalibrationSubsample, ...], client: ClientIdentity) -> None:
    if any(subsample.client != client for subsample in subsamples):
        raise ScientificContractError(
            "subsample references must belong to the manifest client",
            subject=ContractSubject.CALIBRATION,
        )


def _require_nested_subsamples(subsamples: tuple[CalibrationSubsample, ...]) -> None:
    if len(subsamples) < 2:
        return

    cached_sets = [subsample.stable_row_id_set for subsample in subsamples]
    for smaller, larger in zip(cached_sets, cached_sets[1:], strict=False):
        if not smaller.issubset(larger):
            raise ScientificContractError(
                "a smaller calibration subsample must be a subset of the same replicate's larger subsample",
                subject=ContractSubject.CALIBRATION,
            )
