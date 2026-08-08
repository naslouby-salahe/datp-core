"""Checkpoint inventory, persistence, integrity, and non-test selection contracts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import model_validator

from datp_core.artifacts.provenance import Checksum, checksum_file
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.core.identifiers import (
    CheckpointSelectionRule,
    CheckpointStatus,
    ContractSubject,
    SerializationFormat,
)
from datp_core.core.numeric import MetricValue, RoundNumber, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import AutoencoderArchitecture, FederatedTrainingCoordinate

if TYPE_CHECKING:
    from datp_core.detector.training.centralized import CentralizedTrainingCoordinate


class CheckpointProtocol(StrictModel):
    candidates: tuple[RoundNumber, ...]
    maximum_round: RoundNumber

    @model_validator(mode="after")
    def validate_candidates(self) -> "CheckpointProtocol":
        values = tuple(candidate.value for candidate in self.candidates)
        if not values or values != tuple(sorted(values)) or len(frozenset(values)) != len(values):
            raise ValueError("checkpoint candidates must be unique and ordered")
        if values[-1] != self.maximum_round.value:
            raise ValueError("maximum round must be the final checkpoint candidate")
        return self


CHECKPOINT_PROTOCOL = CheckpointProtocol(
    candidates=tuple(RoundNumber(value) for value in (25, 50, 75, 100, 125, 150, 200)),
    maximum_round=RoundNumber(200),
)
CHECKPOINT_SELECTION_RULE = CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND
RETAINED_CHECKPOINT_STATUSES = frozenset(
    {
        CheckpointStatus.CANDIDATE,
        CheckpointStatus.STABILITY_EVIDENCE,
        CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    }
)


def require_non_test_checkpoint_selection_inputs(
    *,
    selection_rule: CheckpointSelectionRule,
    held_out_metrics: Sequence[MetricValue] | None,
    attack_labels_present: bool,
    branch_label: str,
) -> None:
    if held_out_metrics is not None:
        raise LeakageError(
            f"held-out evaluation outcomes cannot influence {branch_label} checkpoint selection",
            subject=ContractSubject.HELD_OUT_METRICS,
        )
    if attack_labels_present:
        raise LeakageError(
            f"attack labels cannot influence {branch_label} checkpoint selection",
            subject=ContractSubject.ATTACK_LABELS,
        )
    if selection_rule is not CHECKPOINT_SELECTION_RULE:
        raise ScientificContractError(
            f"unsupported {branch_label} checkpoint selection rule",
            subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
        )


def fixed_terminal_checkpoint_status(round_number: RoundNumber, maximum_round: RoundNumber) -> CheckpointStatus:
    return (
        CheckpointStatus.SELECTED_BY_NON_TEST_RULE
        if round_number == maximum_round
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


class CheckpointIntegrityContract(PersistedCheckpoint, Protocol):
    pass


@dataclass(frozen=True, slots=True)
class CheckpointCandidate:
    coordinate: FederatedTrainingCoordinate
    round_number: RoundNumber
    tensor_path: Path
    tensor_checksum: Checksum
    mean_training_loss: MetricValue
    status: CheckpointStatus
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    client: ClientIdentity | None = None

    def __post_init__(self) -> None:
        if self.status not in RETAINED_CHECKPOINT_STATUSES:
            raise ScientificContractError("checkpoint candidate has an invalid status", subject=self.status)


@dataclass(frozen=True, slots=True)
class CheckpointDecision:
    coordinate: FederatedTrainingCoordinate
    selected: CheckpointCandidate
    candidates: tuple[CheckpointCandidate, ...]
    checkpoint_protocol: CheckpointProtocol
    selection_rule: CheckpointSelectionRule
    status: CheckpointStatus

    def __post_init__(self) -> None:
        if not self.candidates or self.selected not in self.candidates:
            raise ScientificContractError(
                "selected checkpoint must be one of the retained candidates",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if self.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            raise ScientificContractError("checkpoint decision status must be selected-by-rule", subject=self.status)
        if self.selection_rule is not CHECKPOINT_SELECTION_RULE:
            raise ScientificContractError(
                "checkpoint decision must use the fixed terminal selection rule",
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )
        if self.selected.round_number != self.checkpoint_protocol.maximum_round:
            raise ScientificContractError(
                "selected checkpoint must equal the declared maximum round",
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointSetEntry:
    round_number: RoundNumber
    tensor_checksum: Checksum
    status: CheckpointStatus
    client: ClientIdentity | None = None


@dataclass(frozen=True, slots=True)
class DittoCheckpointCandidate:
    global_candidate: CheckpointCandidate
    personalized_candidates: tuple[CheckpointCandidate, ...]

    def __post_init__(self) -> None:
        if not self.personalized_candidates:
            raise ValueError("Ditto checkpoint candidates require personalized client checkpoints")
        clients = tuple(candidate.client for candidate in self.personalized_candidates)
        if any(client is None for client in clients):
            raise ScientificContractError(
                "Ditto personalized checkpoint candidates require client identities",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        if len(frozenset(clients)) != len(clients):
            raise ScientificContractError(
                "Ditto personalized checkpoint candidates must be unique by client",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
        if any(
            candidate.round_number != self.global_candidate.round_number for candidate in self.personalized_candidates
        ):
            raise ScientificContractError(
                "Ditto global and personalized candidates must share one checkpoint round",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )


@dataclass(frozen=True, slots=True)
class CentralizedCheckpointCandidate:
    coordinate: CentralizedTrainingCoordinate
    round_number: RoundNumber
    tensor_path: Path
    tensor_checksum: Checksum
    mean_training_loss: MetricValue
    status: CheckpointStatus
    preprocessing_state_checksum: Checksum
    split_manifest_checksum: Checksum
    training_seed: Seed
    autoencoder_widths: AutoencoderArchitecture

    def __post_init__(self) -> None:
        if self.status not in RETAINED_CHECKPOINT_STATUSES:
            raise ScientificContractError("centralized checkpoint candidate has an invalid status", subject=self.status)


@dataclass(frozen=True, slots=True)
class CentralizedCheckpointDecision:
    coordinate: CentralizedTrainingCoordinate
    selected: CentralizedCheckpointCandidate
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    checkpoint_protocol: CheckpointProtocol
    selection_rule: CheckpointSelectionRule
    status: CheckpointStatus

    def __post_init__(self) -> None:
        if not self.candidates or self.selected not in self.candidates:
            raise ScientificContractError(
                "selected checkpoint must be one of the retained candidates",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if self.status is not CheckpointStatus.SELECTED_BY_NON_TEST_RULE:
            raise ScientificContractError(
                "centralized checkpoint decision status must be selected-by-rule", subject=self.status
            )
        if self.selection_rule is not CHECKPOINT_SELECTION_RULE:
            raise ScientificContractError(
                "centralized checkpoint decision must use the fixed terminal selection rule",
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )
        if self.selected.round_number != self.checkpoint_protocol.maximum_round:
            raise ScientificContractError(
                "selected checkpoint must equal the declared maximum round",
                subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedCheckpointSetEntry:
    round_number: RoundNumber
    tensor_checksum: Checksum
    status: CheckpointStatus


def validate_persisted_checkpoint_file(
    path: Path,
    checksum: Checksum,
    *,
    serialization_format: SerializationFormat = SerializationFormat.SAFETENSORS,
) -> None:
    if not path.is_file():
        raise ArtifactIntegrityError(
            "checkpoint candidate tensor file is missing", subject=ContractSubject.ARTIFACT_PATH
        )
    if checksum_file(path) != checksum:
        raise ArtifactIntegrityError("checkpoint candidate checksum mismatch", subject=ContractSubject.ARTIFACT_PATH)
    if path.suffix != f".{serialization_format.value}":
        raise ArtifactIntegrityError(
            f"checkpoint must use {serialization_format.value} serialization",
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
            "checkpoint candidate rounds must equal the declared unique ordered protocol",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    paths = tuple(candidate.tensor_path for candidate in ordered)
    if len(frozenset(paths)) != len(paths):
        raise ArtifactIntegrityError(
            "checkpoint candidate paths must be unique", subject=ContractSubject.CHECKPOINT_CANDIDATES
        )
    return ordered


def validate_checkpoint_inventory_files[CandidateT: CheckpointIntegrityContract](
    candidates: Sequence[CandidateT],
) -> None:
    for candidate in candidates:
        validate_persisted_checkpoint_file(candidate.tensor_path, candidate.tensor_checksum)


def select_terminal_checkpoint[CandidateT: PersistedCheckpoint](
    candidates: Sequence[CandidateT],
    maximum_round: RoundNumber,
    *,
    rebuild: Callable[[CandidateT, CheckpointStatus], CandidateT],
) -> tuple[tuple[CandidateT, ...], CandidateT]:
    statused: list[CandidateT] = []
    selected: CandidateT | None = None
    for candidate in candidates:
        status = fixed_terminal_checkpoint_status(candidate.round_number, maximum_round)
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
