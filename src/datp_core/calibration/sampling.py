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
from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import CalibrationSize, ReplicateIndex, RowCount, Seed, checksum_text
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity


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
    ordered = tuple(sorted(references, key=lambda reference: reference.stable_row_id))
    generator = default_rng(replicate_seed(training_seed, client, replicate_index).value)
    permutation = generator.permutation(len(ordered))
    permuted = tuple(ordered[index] for index in permutation)

    subsamples: list[CalibrationSubsample] = []
    unavailable_sizes: list[CalibrationSize] = []
    for size in sorted(sizes, key=lambda item: item.value):
        if size > len(permuted):
            unavailable_sizes.append(size)
            continue
        subsamples.append(
            CalibrationSubsample(
                client=client,
                size=size,
                replicate_index=replicate_index,
                references=permuted[: size.value],
            )
        )
    return CalibrationReplicateManifest(
        client=client,
        coordinate=coordinate,
        training_seed=training_seed,
        replicate_index=replicate_index,
        full_calibration_count=RowCount(len(permuted)),
        subsamples=tuple(subsamples),
        unavailable_sizes=tuple(unavailable_sizes),
        unavailable_reason=(
            CalibrationUnavailableReason.CALIBRATION_SIZE_EXCEEDS_SOURCE if unavailable_sizes else None
        ),
    )
