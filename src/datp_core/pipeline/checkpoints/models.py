"""Shared structural checkpoint contracts without branch-specific science."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from datp_core.domain.enums import CheckpointStatus, ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, RoundNumber

RETAINED_CHECKPOINT_STATUSES = frozenset(
    {
        CheckpointStatus.CANDIDATE,
        CheckpointStatus.STABILITY_EVIDENCE,
        CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    }
)


@dataclass(frozen=True, slots=True, eq=False, kw_only=True)
class InMemoryModelSnapshot[StateT]:
    """Transient model state that must never be reconstructed from persisted metadata."""

    round_number: RoundNumber
    state: StateT
    mean_training_loss: MetricValue


@runtime_checkable
class PersistedCheckpoint(Protocol):
    """Minimum persisted-checkpoint shape shared by centralized and federated branches."""

    round_number: RoundNumber
    tensor_path: Path
    tensor_checksum: Checksum
    mean_training_loss: MetricValue
    status: CheckpointStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointProvenance:
    preprocessing_checksum: Checksum
    split_checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class PersistedCheckpointReference[CoordinateT, OwnerT]:
    """Branch-neutral persisted checkpoint reference with explicit ownership."""

    coordinate: CoordinateT
    owner: OwnerT | None
    round_number: RoundNumber
    tensor_path: Path
    tensor_checksum: Checksum
    mean_training_loss: MetricValue
    status: CheckpointStatus
    provenance: CheckpointProvenance

    def __post_init__(self) -> None:
        if self.status not in RETAINED_CHECKPOINT_STATUSES:
            raise ScientificContractError(
                "persisted checkpoint reference has an invalid retained status",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
