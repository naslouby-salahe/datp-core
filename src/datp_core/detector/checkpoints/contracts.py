"""Checkpoint inventory, persistence, integrity, and non-test selection contracts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import model_validator

from datp_core.artifacts.provenance import Checksum
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ArtifactIntegrityError,
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CheckpointStatus,
    ContractSubject,
    SerializationFormat,
)
from datp_core.core.numeric import MetricValue, RoundNumber


@dataclass(frozen=True, slots=True)
class ConvergenceProtocol:
    """Convergence early-stop on the relative change of weighted benign validation loss."""

    rounds_initial: RoundNumber
    relative_threshold: float
    window: int

    def __post_init__(self) -> None:
        if self.rounds_initial.value < 1:
            raise ValueError("rounds_initial must be >= 1")
        if self.window < 2:
            raise ValueError("window must be >= 2")
        if self.relative_threshold <= 0.0:
            raise ValueError("relative_threshold must be positive")


class CheckpointProtocol(StrictModel):
    candidates: tuple[RoundNumber, ...]
    maximum_round: RoundNumber
    convergence: ConvergenceProtocol | None = None

    @model_validator(mode="after")
    def validate_candidates(self) -> CheckpointProtocol:
        values = tuple(candidate.value for candidate in self.candidates)
        if not values or values != tuple(sorted(values)) or len(frozenset(values)) != len(values):
            raise ValueError("checkpoint candidates must be unique and ordered")
        if values[-1] != self.maximum_round.value:
            raise ValueError("maximum round must be the final checkpoint candidate")
        if self.convergence is not None and self.convergence.rounds_initial.value > self.maximum_round.value:
            raise ValueError("rounds_initial cannot exceed the maximum round")
        return self


def realized_candidate_rounds(
    protocol: CheckpointProtocol,
    final_round: RoundNumber,
) -> tuple[RoundNumber, ...]:
    """Declare the realized checkpoint inventory for a training run that stopped at ``final_round``.

    The declared grid candidates at or below the final completed round are retained as
    stability evidence, and the final completed round itself is the terminal candidate.
    """
    if final_round.value < 1 or final_round.value > protocol.maximum_round.value:
        raise ScientificContractError(
            ErrorMessage("final completed round must lie within the declared checkpoint protocol"),
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    retained = tuple(candidate for candidate in protocol.candidates if candidate.value < final_round.value)
    if final_round in retained:
        return retained
    return retained + (final_round,)


def terminal_checkpoint_status(round_number: RoundNumber, terminal_round: RoundNumber) -> CheckpointStatus:
    return (
        CheckpointStatus.SELECTED_BY_NON_TEST_RULE
        if round_number == terminal_round
        else CheckpointStatus.STABILITY_EVIDENCE
    )


@runtime_checkable
class PersistedCheckpoint(Protocol):
    @property
    def round_number(self) -> RoundNumber: ...

    @property
    def tensor_path(self) -> Path: ...

    @property
    def tensor_checksum(self) -> Checksum: ...

    @property
    def mean_training_loss(self) -> MetricValue: ...

    @property
    def status(self) -> CheckpointStatus: ...


@dataclass(frozen=True, slots=True)
class TerminalCheckpointSelection[CandidateT: PersistedCheckpoint]:
    candidates: tuple[CandidateT, ...]
    selected: CandidateT


def validate_persisted_checkpoint_file(
    path: Path,
    checksum: Checksum,
    *,
    serialization_format: SerializationFormat = SerializationFormat.SAFETENSORS,
) -> None:
    if not path.is_file():
        raise ArtifactIntegrityError(
            ErrorMessage("checkpoint candidate tensor file is missing"), subject=ContractSubject.ARTIFACT_PATH
        )
    if Checksum.from_file(path) != checksum:
        raise ArtifactIntegrityError(
            ErrorMessage("checkpoint candidate checksum mismatch"), subject=ContractSubject.ARTIFACT_PATH
        )
    if path.suffix != f".{serialization_format.value}":
        raise ArtifactIntegrityError(
            ErrorMessage(f"checkpoint must use {serialization_format.value} serialization"),
            subject=ContractSubject.ARTIFACT_PATH,
        )


def validate_ordered_checkpoint_inventory[CandidateT: PersistedCheckpoint](
    candidates: Sequence[CandidateT],
    expected_rounds: tuple[RoundNumber, ...],
) -> tuple[CandidateT, ...]:
    ordered = tuple(candidates)
    observed = tuple(candidate.round_number for candidate in ordered)
    if observed != expected_rounds or len(frozenset(observed)) != len(observed):
        raise ArtifactIntegrityError(
            ErrorMessage("checkpoint candidate rounds must equal the declared unique ordered protocol"),
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    paths = tuple(candidate.tensor_path for candidate in ordered)
    if len(frozenset(paths)) != len(paths):
        raise ArtifactIntegrityError(
            ErrorMessage("checkpoint candidate paths must be unique"), subject=ContractSubject.CHECKPOINT_CANDIDATES
        )
    return ordered


def select_terminal_checkpoint[CandidateT: PersistedCheckpoint](
    candidates: Sequence[CandidateT],
    *,
    terminal_round: RoundNumber,
    rebuild: Callable[[CandidateT, CheckpointStatus], CandidateT],
) -> TerminalCheckpointSelection[CandidateT]:
    statused: list[CandidateT] = []
    selected: CandidateT | None = None
    for candidate in candidates:
        status = terminal_checkpoint_status(candidate.round_number, terminal_round)
        rebuilt = rebuild(candidate, status)
        statused.append(rebuilt)
        if status is CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            if selected is not None:
                raise ScientificContractError(
                    ErrorMessage("terminal selection produced multiple selected candidates"),
                    subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
                )
            selected = rebuilt
    if selected is None:
        raise ArtifactIntegrityError(
            ErrorMessage("declared terminal-round checkpoint candidate is missing"),
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return TerminalCheckpointSelection(candidates=tuple(statused), selected=selected)
