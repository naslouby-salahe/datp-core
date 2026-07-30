"""Stage: select the centralized primary checkpoint under FIXED_TERMINAL_MAXIMUM_ROUND."""

from dataclasses import dataclass

from datp_core.centralized_reference.checkpointing import (
    CentralizedCheckpointCandidate,
    CentralizedCheckpointDecision,
    select_centralized_checkpoint,
    validate_candidate_coordinates,
)
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import StageOperationId
from datp_core.domain.values import Checksum, MetricValue, Seed
from datp_core.protocols.models import CheckpointProtocol
from datp_core.protocols.training import CHECKPOINT_SELECTION_RULE


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
    stage: StageOperationId
    decision: CentralizedCheckpointDecision


def select_centralized_reference_checkpoint_stage(
    request: SelectCentralizedCheckpointRequest,
) -> SelectCentralizedCheckpointResult:
    validate_candidate_coordinates(
        request.candidates,
        request.coordinate,
        preprocessing_checksum=request.preprocessing_checksum,
        split_checksum=request.split_checksum,
        training_seed=request.training_seed,
    )
    decision = select_centralized_checkpoint(
        request.candidates,
        request.checkpoint_protocol,
        selection_rule=CHECKPOINT_SELECTION_RULE,
        held_out_metrics=request.held_out_metrics,
        attack_labels_present=request.attack_labels_present,
    )
    return SelectCentralizedCheckpointResult(
        stage=StageOperationId.SELECT_CENTRALIZED_REFERENCE_CHECKPOINT,
        decision=decision,
    )
