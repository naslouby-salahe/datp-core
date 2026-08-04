"""Stage: select the centralized primary checkpoint under the fixed terminal rule."""

from datp_core.centralized_reference.checkpointing import (
    select_centralized_checkpoint,
    validate_candidate_coordinates,
)
from datp_core.orchestration.commands.checkpoints import (
    SelectCentralizedCheckpointRequest as _SelectCentralizedCheckpointRequest,
    SelectCentralizedCheckpointResult as _SelectCentralizedCheckpointResult,
)
from datp_core.protocols.training import CHECKPOINT_SELECTION_RULE


def select_centralized_reference_checkpoint_stage(
    request: _SelectCentralizedCheckpointRequest,
) -> _SelectCentralizedCheckpointResult:
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
    return _SelectCentralizedCheckpointResult(decision=decision)
