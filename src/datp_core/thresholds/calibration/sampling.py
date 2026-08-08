"""Deterministic nested without-replacement calibration subsampling."""

from dataclasses import dataclass

from numpy.random import default_rng

from datp_core.artifacts.provenance import checksum_text
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ContractSubject, StableRowId
from datp_core.core.numeric import CalibrationSize, ReplicateIndex, RowCount, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.calibration.eligibility import (
    CalibrationSampleReference,
    CalibrationUnavailableReason,
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
        client = self.references[0].client
        stable_row_ids = tuple(reference.stable_row_id for reference in self.references)
        if any(reference.client != client for reference in self.references):
            raise ScientificContractError(
                "subsample references must belong to exactly one client",
                subject=ContractSubject.CALIBRATION,
            )
        if len(frozenset(stable_row_ids)) != len(stable_row_ids):
            raise ScientificContractError(
                "subsample references must be drawn without replacement",
                subject=ContractSubject.CALIBRATION,
            )

    @property
    def client(self) -> ClientIdentity:
        if not self.references:
            raise ScientificContractError(
                "empty calibration subsamples have no client identity",
                subject=ContractSubject.CALIBRATION,
            )
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
        sizes = tuple(subsample.size.value for subsample in self.subsamples)
        if sizes != tuple(sorted(sizes)):
            raise ScientificContractError(
                "subsamples must be ordered by ascending calibration size",
                subject=ContractSubject.CALIBRATION,
            )
        if any(subsample.client != self.client for subsample in self.subsamples):
            raise ScientificContractError(
                "subsample references must belong to the manifest client",
                subject=ContractSubject.CALIBRATION,
            )
        for smaller, larger in zip(self.subsamples, self.subsamples[1:], strict=False):
            if not smaller.stable_row_id_set.issubset(larger.stable_row_id_set):
                raise ScientificContractError(
                    "smaller calibration subsamples must be nested in larger sizes within a replicate",
                    subject=ContractSubject.CALIBRATION,
                )


def replicate_seed(training_seed: Seed, client: ClientIdentity, replicate_index: ReplicateIndex) -> Seed:
    payload = f"{training_seed.value}|{client.population.value}|{client.client_id}|{replicate_index.value}"
    return Seed(int(checksum_text(payload).value, 16))


def build_calibration_replicate(
    *,
    client: ClientIdentity,
    coordinate: FederatedTrainingCoordinate,
    training_seed: Seed,
    replicate_index: ReplicateIndex,
    references: tuple[CalibrationSampleReference, ...],
    sizes: tuple[CalibrationSize, ...],
) -> CalibrationReplicateManifest:
    if any(reference.client != client for reference in references):
        raise ScientificContractError(
            "calibration references must belong to the replicate client",
            subject=ContractSubject.CALIBRATION,
        )
    if len(frozenset(reference.stable_row_id for reference in references)) != len(references):
        raise ScientificContractError(
            "full calibration references must be unique by stable source-row identity",
            subject=ContractSubject.CALIBRATION,
        )
    ordered = tuple(sorted(references, key=lambda reference: reference.stable_row_id))
    permutation = default_rng(replicate_seed(training_seed, client, replicate_index).value).permutation(len(ordered))
    permuted = tuple(ordered[index] for index in permutation)
    sorted_sizes = tuple(sorted(sizes, key=lambda item: item.value))
    if len(frozenset(sorted_sizes)) != len(sorted_sizes):
        raise ScientificContractError(
            "calibration subsampling sizes must be unique",
            subject=ContractSubject.CALIBRATION,
        )
    feasible = tuple(size for size in sorted_sizes if size.value <= len(permuted))
    unavailable = tuple(size for size in sorted_sizes if size.value > len(permuted))
    subsamples = tuple(
        CalibrationSubsample(
            size=size,
            replicate_index=replicate_index,
            references=permuted[: size.value],
        )
        for size in feasible
    )
    return CalibrationReplicateManifest(
        client=client,
        coordinate=coordinate,
        training_seed=training_seed,
        replicate_index=replicate_index,
        full_calibration_count=RowCount(len(permuted)),
        subsamples=subsamples,
        unavailable_sizes=unavailable,
        unavailable_reason=(CalibrationUnavailableReason.CALIBRATION_SIZE_EXCEEDS_SOURCE if unavailable else None),
    )
