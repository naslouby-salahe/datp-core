from dataclasses import fields

from datp_core.application.ports.persistence import SaveRecoveryStateRequest, SaveScientificCheckpointRequest
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.learning.checkpoints import CheckpointDescriptor, RecoveryState


def test_checkpoint_requests_expose_only_typed_references_at_the_application_boundary() -> None:
    scientific_fields = {field.name: field.type for field in fields(SaveScientificCheckpointRequest)}
    recovery_fields = {field.name: field.type for field in fields(SaveRecoveryStateRequest)}

    assert scientific_fields == {"checkpoint": CheckpointDescriptor, "staged_artifact": ArtifactRef}
    assert recovery_fields == {"recovery_state": RecoveryState}
