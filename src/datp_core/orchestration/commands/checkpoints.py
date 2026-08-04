"""Typed checkpoint-selection commands and stage outcomes."""

from dataclasses import dataclass
from typing import ClassVar

from datp_core.centralized_reference.checkpointing import (
    CentralizedCheckpointCandidate,
    CentralizedCheckpointDecision,
)
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import StageOperationId
from datp_core.domain.values import Checksum, MetricValue, Seed
from datp_core.learning.federated.models import (
    CheckpointCandidate,
    CheckpointDecision,
    FederatedTrainingCoordinate,
)
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import CheckpointProtocol


@dataclass(frozen=True, slots=True)
class SelectFederatedCheckpointRequest:
    coordinate: FederatedTrainingCoordinate
    client: ClientIdentity | None
    candidates: tuple[CheckpointCandidate, ...]
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    held_out_metrics: tuple[MetricValue, ...] | None
    attack_labels_present: bool


@dataclass(frozen=True, slots=True)
class SelectFederatedCheckpointResult:
    stage: ClassVar[StageOperationId] = StageOperationId.SELECT_FEDERATED_CHECKPOINT
    decision: CheckpointDecision


@dataclass(frozen=True, slots=True)
class SelectCentralizedCheckpointRequest:
    coordinate: CentralizedTrainingCoordinate
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    checkpoint_protocol: CheckpointProtocol
    preprocessing_checksum: Checksum
    split_checksum: Checksum
    training_seed: Seed
    held_out_metrics: tuple[MetricValue, ...] | None
    attack_labels_present: bool


@dataclass(frozen=True, slots=True)
class SelectCentralizedCheckpointResult:
    stage: ClassVar[StageOperationId] = StageOperationId.SELECT_CENTRALIZED_REFERENCE_CHECKPOINT
    decision: CentralizedCheckpointDecision
