"""Deterministic, nested, without-replacement calibration subsampling.

One held-out random permutation of a client's full benign calibration row order is
derived from `(training_seed, population, client_id, replicate_index)` via a stable
content hash, and every declared size is read as a prefix of that single
permutation. Reading prefixes of one seeded permutation is what makes the size-
nesting requirement exact by construction rather than by post-hoc verification.
"""

from numpy.random import default_rng

from datp_core.calibration.models import (
    CalibrationReplicateManifest,
    CalibrationSampleReference,
    CalibrationSubsample,
    CalibrationUnavailableReason,
)
from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import checksum_text
from datp_core.domain.values.counts import CalibrationSize, ReplicateIndex, RowCount, Seed
from datp_core.learning.federated.models import FederatedTrainingCoordinate


def replicate_seed(training_seed: Seed, client: ClientIdentity, replicate_index: ReplicateIndex) -> Seed:
    """Derive one deterministic permutation seed for a (seed, client, replicate) triple."""
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
    """Construct one deterministic, nested subsampling replicate for a client.

    ``sizes`` must be the declared calibration-size grid; a size larger than the
    client's full benign calibration count is recorded as typed unavailability
    rather than silently substituting a smaller size.
    """
    if any(reference.client != client for reference in references):
        raise ScientificContractError(
            "calibration references must belong to the replicate's client",
            subject=ContractSubject.CALIBRATION,
        )

    ordered_list = sorted(references, key=lambda reference: reference.stable_row_id)
    generator = default_rng(replicate_seed(training_seed, client, replicate_index).value)

    # We maintain the exact sequence of `permutation(int)` rather than in-place `shuffle(list)`
    # to guarantee exact cryptographic/scientific parity with historical artifacts.
    permutation = generator.permutation(len(ordered_list))
    permuted = tuple(ordered_list[index] for index in permutation)

    full_count = len(permuted)
    sorted_sizes = sorted(sizes, key=lambda item: item.value)

    split_index = len(sorted_sizes)
    for i, size in enumerate(sorted_sizes):
        if size.value > full_count:
            split_index = i
            break

    subsamples = tuple(
        CalibrationSubsample(
            size=size,
            replicate_index=replicate_index,
            references=permuted[: size.value],
        )
        for size in sorted_sizes[:split_index]
    )

    return CalibrationReplicateManifest(
        client=client,
        coordinate=coordinate,
        training_seed=training_seed,
        replicate_index=replicate_index,
        full_calibration_count=RowCount(full_count),
        subsamples=subsamples,
        unavailable_sizes=tuple(sorted_sizes[split_index:]),
        unavailable_reason=(
            CalibrationUnavailableReason.CALIBRATION_SIZE_EXCEEDS_SOURCE if split_index < len(sorted_sizes) else None
        ),
    )
