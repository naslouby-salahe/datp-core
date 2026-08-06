"""Layer-neutral checkpoint inventory, integrity, and selection invariants."""

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import CheckpointStatus, ContractSubject, SerializationFormat
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values.checksums import Checksum, checksum_file
from datp_core.domain.values.counts import RoundNumber


class CheckpointProtocol(StrictModel):
    candidates: tuple[RoundNumber, ...]
    maximum_round: RoundNumber

    @model_validator(mode="after")
    def validate_candidates(self) -> "CheckpointProtocol":
        values = tuple(candidate.value for candidate in self.candidates)
        if not values or values != tuple(sorted(values)) or len(set(values)) != len(values):
            raise ValueError("checkpoint candidates must be unique and ordered")
        if values[-1] != self.maximum_round.value:
            raise ValueError("maximum round must be the final checkpoint candidate")
        return self


class PersistedCheckpointContract(Protocol):
    @property
    def round_number(self) -> RoundNumber: ...

    @property
    def tensor_path(self) -> Path: ...


class CheckpointIntegrityContract(PersistedCheckpointContract, Protocol):
    @property
    def tensor_checksum(self) -> Checksum: ...


def validate_persisted_checkpoint_file(
    path: Path,
    checksum: Checksum,
    *,
    serialization_format: SerializationFormat = SerializationFormat.SAFETENSORS,
) -> None:
    if not path.is_file():
        raise ArtifactIntegrityError(
            "checkpoint candidate tensor file is missing",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if checksum_file(path) != checksum:
        raise ArtifactIntegrityError(
            "checkpoint candidate checksum mismatch",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if path.suffix != f".{serialization_format.value}":
        raise ArtifactIntegrityError(
            f"checkpoint must use {serialization_format.value} serialization",
            subject=ContractSubject.ARTIFACT_PATH,
        )


def validate_ordered_checkpoint_inventory[CandidateT: PersistedCheckpointContract](
    candidates: Sequence[CandidateT],
    expected_rounds: tuple[RoundNumber, ...],
) -> tuple[CandidateT, ...]:
    ordered = tuple(candidates)
    observed = tuple(candidate.round_number for candidate in ordered)
    if observed != expected_rounds:
        raise ArtifactIntegrityError(
            "checkpoint candidate rounds must equal the declared ordered protocol",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    if len(frozenset(observed)) != len(observed):
        raise ArtifactIntegrityError(
            "duplicate checkpoint candidates are forbidden",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    paths = tuple(candidate.tensor_path for candidate in ordered)
    if len(frozenset(paths)) != len(paths):
        raise ArtifactIntegrityError(
            "checkpoint candidate paths must be unique",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return ordered


def validate_checkpoint_inventory_files[CandidateT: CheckpointIntegrityContract](
    candidates: Sequence[CandidateT],
) -> None:
    for candidate in candidates:
        validate_persisted_checkpoint_file(candidate.tensor_path, candidate.tensor_checksum)


def select_terminal_checkpoint[CandidateT: PersistedCheckpointContract](
    candidates: Sequence[CandidateT],
    maximum_round: RoundNumber,
    *,
    rebuild: Callable[[CandidateT, CheckpointStatus], CandidateT],
) -> tuple[tuple[CandidateT, ...], CandidateT]:
    statused: list[CandidateT] = []
    selected: CandidateT | None = None
    for candidate in candidates:
        status = (
            CheckpointStatus.SELECTED_BY_NON_TEST_RULE
            if candidate.round_number == maximum_round
            else CheckpointStatus.STABILITY_EVIDENCE
        )
        rebuilt = rebuild(candidate, status)
        statused.append(rebuilt)
        if status is CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            if selected is not None:
                raise ScientificContractError(
                    "fixed-terminal selection produced multiple selected candidates",
                    subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
                )
            selected = rebuilt
    if selected is None:
        raise ArtifactIntegrityError(
            "declared maximum-round checkpoint candidate is missing",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return tuple(statused), selected
