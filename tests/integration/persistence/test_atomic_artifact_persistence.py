from os import replace as os_replace
from pathlib import Path

import pytest

from datp_core.application.ports.persistence import ValidateArtifactRequest, WriteArtifactRequest
from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    RunArtifactKey,
    SerializationFormat,
    StorageRootKind,
    StorageRootSpec,
    StorageVisibility,
    WriteDisposition,
)
from datp_core.domain.artifacts.lineage import IntegrityStatus, StageFingerprint
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion
from datp_core.domain.errors import PartialArtifactError
from datp_core.infrastructure.persistence.artifacts import FileArtifactStore
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash
from datp_core.infrastructure.persistence.paths import ArtifactPathResolver, ResolveArtifactLocationRequest
from datp_core.infrastructure.persistence.roots import bind_storage_root


def _request(content: bytes) -> WriteArtifactRequest:
    return WriteArtifactRequest(
        key=RunArtifactKey(
            artifact_type=ArtifactType.RESULT_FREEZE,
            stage_identity=StageFingerprint(value="e" * 64),
            namespace=ArtifactNamespace.TEST_SANDBOX,
        ),
        artifact=ArtifactRef(
            artifact_id=ArtifactId(value="artifact-" + "f" * 64),
            artifact_type=ArtifactType.RESULT_FREEZE,
            content_hash=blake3_bytes_content_hash(content),
            schema_version=ArtifactSchemaVersion(value="v1"),
            serialization_format=SerializationFormat.JSON,
        ),
        content=content,
        write_disposition=WriteDisposition.ATOMIC_STAGE_COMMIT,
    )


def test_synthetic_single_file_commit_uses_the_destination_filesystem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = FileArtifactStore(
        root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.TEST_SANDBOX, visibility=StorageVisibility.TEST_ISOLATED),
            absolute_path=tmp_path,
        )
    )
    request = _request(b"synthetic atomic persistence integration")
    same_filesystem: list[bool] = []

    def checked_replace(source: str | Path, destination: str | Path) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        same_filesystem.append(source_path.stat().st_dev == destination_path.parent.stat().st_dev)
        os_replace(source_path, destination_path)

    monkeypatch.setattr("datp_core.infrastructure.persistence.artifacts.replace", checked_replace)
    store.write_atomically(request)

    validation = store.validate_integrity(ValidateArtifactRequest(key=request.key, artifact=request.artifact))
    assert same_filesystem == [True, True]
    assert validation.integrity is IntegrityStatus.INTACT
    assert not tuple(path for path in tmp_path.rglob(".artifact-*") if path.name != ".artifact-manifests")


def test_synthetic_killed_mid_write_cannot_publish_a_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = FileArtifactStore(
        root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.TEST_SANDBOX, visibility=StorageVisibility.TEST_ISOLATED),
            absolute_path=tmp_path,
        )
    )
    request = _request(b"synthetic interrupted integration")

    def killed_before_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("simulated killed writer")

    monkeypatch.setattr("datp_core.infrastructure.persistence.artifacts.replace", killed_before_replace)
    with pytest.raises(PartialArtifactError):
        store.write_atomically(request)

    assert not (tmp_path / ".artifact-manifests" / request.artifact.artifact_id.value).exists()
    final_path = (
        ArtifactPathResolver()
        .resolve(ResolveArtifactLocationRequest(key=request.key, root=store.root, artifact=request.artifact))
        .absolute_path
    )
    assert not final_path.exists()
