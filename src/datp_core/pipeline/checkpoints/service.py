"""Shared checkpoint inventory, file-integrity, and terminal-selection services."""

from collections.abc import Callable, Sequence
from pathlib import Path

from datp_core.domain.enums import CheckpointStatus, ContractSubject, SerializationFormat
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import Checksum, RoundNumber, checksum_file
from datp_core.pipeline.checkpoints.models import PersistedCheckpoint


def validate_ordered_checkpoint_inventory[CandidateT: PersistedCheckpoint](
    candidates: Sequence[CandidateT],
    expected_rounds: tuple[RoundNumber, ...],
) -> tuple[CandidateT, ...]:
    """Require an exact ordered candidate inventory with unique rounds and paths."""
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


def validate_persisted_checkpoint_file(
    path: Path,
    checksum: Checksum,
    *,
    serialization_format: SerializationFormat = SerializationFormat.SAFETENSORS,
) -> None:
    """Validate one persisted checkpoint without loading branch-specific model state."""
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


def select_terminal_checkpoint[CandidateT: PersistedCheckpoint](
    candidates: Sequence[CandidateT],
    maximum_round: RoundNumber,
    *,
    rebuild: Callable[[CandidateT, CheckpointStatus], CandidateT],
) -> tuple[tuple[CandidateT, ...], CandidateT]:
    """Apply the fixed-terminal non-test rule to an already validated inventory."""
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
