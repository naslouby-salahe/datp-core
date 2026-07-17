from pathlib import Path

import pytest
import torch

from datp_core.application.ports.persistence import SaveScientificCheckpointRequest
from datp_core.domain.artifacts.keys import (
    SerializationFormat,
    StorageRootKind,
    StorageRootSpec,
    StorageVisibility,
)
from datp_core.domain.artifacts.lineage import TrainingIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactSchemaVersion,
    CheckpointId,
    StageFingerprint,
)
from datp_core.domain.learning.checkpoints import CheckpointDescriptor, CheckpointProtocol
from datp_core.domain.runtime.seeds import RoundNumber, Seed
from datp_core.infrastructure.persistence.checkpoints import FileCheckpointStore
from datp_core.infrastructure.persistence.hashing import DEFAULT_HASH_CHUNK_SIZE, blake3_file_content_hash
from datp_core.infrastructure.persistence.roots import bind_storage_root
from tests.support.cuda_lane import skip_if_cuda_unavailable


@pytest.mark.cuda
def test_synthetic_cuda_model_checkpoint_descriptor_round_trips(tmp_path: Path) -> None:
    skip_if_cuda_unavailable()
    model = torch.nn.Linear(2, 1, device="cuda")
    staged_state = tmp_path / "staged-state.pt"
    torch.save(model.state_dict(), staged_state)
    restored_state = torch.load(staged_state, map_location="cuda", weights_only=True)
    assert torch.equal(restored_state["weight"], model.state_dict()["weight"])

    content_hash = blake3_file_content_hash(staged_state, chunk_size=DEFAULT_HASH_CHUNK_SIZE)
    artifact = ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + "a" * 64),
        artifact_type=ArtifactType.SCIENTIFIC_CHECKPOINT,
        content_hash=content_hash,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.TORCH_STATE,
    )
    descriptor = CheckpointDescriptor(
        checkpoint_id=CheckpointId(value="checkpoint-" + "b" * 64),
        round=RoundNumber(value=25),
        seed=Seed(value=1),
        training_identity=TrainingIdentity(value=StageFingerprint(value="c" * 64)),
        protocol=CheckpointProtocol.JOURNAL_SCHEDULED,
        artifact_ref=artifact,
        content_hash=content_hash,
        schema_version=artifact.schema_version,
    )
    store = FileCheckpointStore(
        scientific_root=bind_storage_root(
            spec=StorageRootSpec(
                kind=StorageRootKind.SCIENTIFIC_CHECKPOINTS,
                visibility=StorageVisibility.SCIENTIFIC_OUTPUT,
            ),
            absolute_path=tmp_path / "scientific",
        ),
        recovery_root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.RECOVERY_STATE, visibility=StorageVisibility.EPHEMERAL),
            absolute_path=tmp_path / "recovery",
        ),
    )

    result = store.save(SaveScientificCheckpointRequest(checkpoint=descriptor, staged_artifact=artifact))

    assert result.checkpoint == descriptor
