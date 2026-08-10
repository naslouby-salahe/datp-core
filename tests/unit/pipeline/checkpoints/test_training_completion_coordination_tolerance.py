"""The training publication exact-set check must tolerate sibling coordination entries.

Score artifacts publish under the shared training root, so their ``FileLock``
sibling and staging directories land beside the declared training files. Those
coordination entries are not publication content and must not invalidate an
otherwise complete training publication; genuine foreign files still must.
"""

from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    fedavg_coordinate,
)

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.identifiers import CheckpointStatus
from datp_core.core.numeric import MetricValue, Seed
from datp_core.detector.checkpoints.candidates import candidate_tensor_name
from datp_core.detector.checkpoints.documents import CandidateManifest
from datp_core.detector.checkpoints.identities import (
    CandidateManifestKind,
    FederatedHistoryAssetName,
)
from datp_core.detector.checkpoints.publication import (
    build_manifest,
    verify_completion,
    write_completion,
    write_manifest,
)
from datp_core.detector.training.models import CheckpointCandidate


def _published_training(directory: Path) -> tuple[CandidateManifest, Checksum]:
    coordinate = fedavg_coordinate(Seed(0))
    tensor_path = directory / candidate_tensor_name(CHECKPOINT.candidates[0])
    tensor_path.write_bytes(b"tensor-state")
    candidate = CheckpointCandidate(
        coordinate=coordinate,
        round_number=CHECKPOINT.candidates[0],
        client=None,
        tensor_path=tensor_path,
        tensor_checksum=Checksum.from_file(tensor_path),
        mean_training_loss=MetricValue(0.5),
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_set_checksum=Checksum("preprocessing"),
        split_manifest_checksum=Checksum("split"),
    )
    for name in (
        FederatedHistoryAssetName.ROUND_SUMMARY.value,
        FederatedHistoryAssetName.CLIENT_ROUNDS.value,
        FederatedHistoryAssetName.DEVICE_NAME.value,
    ):
        (directory / name).write_bytes(b"history")
    manifest = build_manifest(
        kind=CandidateManifestKind.GLOBAL,
        coordinate=coordinate,
        candidates=(candidate,),
        checkpoint_protocol=CHECKPOINT,
        autoencoder=AUTOENCODER,
        batch_size=BATCH_SIZE,
        preprocessing_state_set_checksum=Checksum("preprocessing"),
        split_manifest_checksum=Checksum("split"),
    )
    write_manifest(directory, manifest)
    digest = write_completion(directory, manifest, include_history=True)
    return manifest, digest


def test_verify_completion_tolerates_sibling_lock_and_staging_entries(tmp_path: Path) -> None:
    manifest, digest = _published_training(tmp_path)

    (tmp_path / "scores.lock").write_text("", encoding="utf-8")
    (tmp_path / ".scores.ab12cd").mkdir()

    assert verify_completion(tmp_path, manifest, include_history=True) == digest


def test_verify_completion_still_rejects_foreign_publication_files(tmp_path: Path) -> None:
    manifest, _ = _published_training(tmp_path)

    (tmp_path / "stray.bin").write_bytes(b"not part of this publication")

    with pytest.raises(ArtifactIntegrityError, match="do not match the exact declared artifact set"):
        verify_completion(tmp_path, manifest, include_history=True)
