"""Centralized and federated checkpoint selection under one pipeline owner."""

from dataclasses import dataclass

from datp_core.domain.values import Checksum, MetricValue, Seed
from datp_core.learning.centralized.training import CentralizedTrainingCoordinate
from datp_core.learning.federated.checkpoints.selection import (
    select_checkpoint,
    validate_candidate_coordinates as validate_federated_candidates,
)
from datp_core.learning.federated.models import (
    CheckpointCandidate,
    CheckpointDecision,
    FederatedTrainingCoordinate,
)
from datp_core.pipeline.checkpoints.records import (
    CentralizedCheckpointCandidate,
    CentralizedCheckpointDecision,
)
from datp_core.pipeline.checkpoints.service import (
    select_centralized_checkpoint,
    validate_centralized_candidate_coordinates,
)
from datp_core.pipeline.execution import PipelineStage
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import CheckpointProtocol
from datp_core.protocols.training import CHECKPOINT_SELECTION_RULE


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectFederatedCheckpointRequest:
    coordinate: FederatedTrainingCoordinate
    client: ClientIdentity | None
    candidates: tuple[CheckpointCandidate, ...]
    checkpoint_protocol: CheckpointProtocol
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    held_out_metrics: tuple[MetricValue, ...] | None
    attack_labels_present: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectFederatedCheckpointResult:
    stage: PipelineStage
    decision: CheckpointDecision


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectCentralizedCheckpointRequest:
    coordinate: CentralizedTrainingCoordinate
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    checkpoint_protocol: CheckpointProtocol
    preprocessing_checksum: Checksum
    split_checksum: Checksum
    training_seed: Seed
    held_out_metrics: tuple[MetricValue, ...] | None
    attack_labels_present: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectCentralizedCheckpointResult:
    stage: PipelineStage
    decision: CentralizedCheckpointDecision


def select_federated_primary_checkpoint(
    request: SelectFederatedCheckpointRequest,
) -> SelectFederatedCheckpointResult:
    validate_federated_candidates(
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
    return SelectFederatedCheckpointResult(stage=PipelineStage.SELECT_CHECKPOINT, decision=decision)


def select_centralized_primary_checkpoint(
    request: SelectCentralizedCheckpointRequest,
) -> SelectCentralizedCheckpointResult:
    validate_centralized_candidate_coordinates(
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
    return SelectCentralizedCheckpointResult(stage=PipelineStage.SELECT_CHECKPOINT, decision=decision)
