"""Stage: select the federated primary checkpoint under FIXED_TERMINAL_MAXIMUM_ROUND."""

from dataclasses import dataclass
from typing import ClassVar

from datp_core.domain.enums import StageOperationId
from datp_core.domain.values import Checksum, MetricValue
from datp_core.learning.federated.checkpoints.selection import select_checkpoint, validate_candidate_coordinates
from datp_core.learning.federated.models import (
    CheckpointCandidate,
    CheckpointDecision,
    FederatedTrainingCoordinate,
)
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import CheckpointProtocol
from datp_core.protocols.training import CHECKPOINT_SELECTION_RULE


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


def select_federated_checkpoint_stage(
    request: SelectFederatedCheckpointRequest,
) -> SelectFederatedCheckpointResult:
    validate_candidate_coordinates(
        request.candidates,
        request.coordinate,
        client=request.client,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )
    decision = select_checkpoint(
        request.candidates,
        request.checkpoint_protocol,
        coordinate=request.coordinate,
        client=request.client,
        selection_rule=CHECKPOINT_SELECTION_RULE,
        held_out_metrics=request.held_out_metrics,
        attack_labels_present=request.attack_labels_present,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )
    return SelectFederatedCheckpointResult(decision=decision)
