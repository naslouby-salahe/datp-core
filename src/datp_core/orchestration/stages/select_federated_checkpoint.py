"""Stage: select the federated primary checkpoint under the fixed terminal rule."""

from datp_core.learning.federated.checkpoints.selection import (
    select_checkpoint,
    validate_candidate_coordinates,
)
from datp_core.orchestration.commands.checkpoints import (
    SelectFederatedCheckpointRequest as _SelectFederatedCheckpointRequest,
)
from datp_core.orchestration.commands.checkpoints import (
    SelectFederatedCheckpointResult as _SelectFederatedCheckpointResult,
)
from datp_core.protocols.training import CHECKPOINT_SELECTION_RULE


def select_federated_checkpoint_stage(
    request: _SelectFederatedCheckpointRequest,
) -> _SelectFederatedCheckpointResult:
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
    return _SelectFederatedCheckpointResult(decision=decision)
