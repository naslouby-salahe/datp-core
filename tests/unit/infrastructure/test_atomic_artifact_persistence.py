from inspect import signature
from pathlib import Path

import pytest

from datp_core.application.ports.persistence import (
    ArtifactLookupRequest,
    ArtifactStore,
    ValidateArtifactRequest,
    WriteArtifactRequest,
)
from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    RunArtifactKey,
    SerializationFormat,
    StorageRootKind,
    StorageRootSpec,
    StorageVisibility,
    WriteDisposition,
)
from datp_core.domain.artifacts.lineage import IntegrityStatus, SchemaCompatibility, StageFingerprint
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion
from datp_core.domain.errors import ArtifactError, PartialArtifactError
from datp_core.infrastructure.persistence.artifacts import FileArtifactStore
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash
from datp_core.infrastructure.persistence.paths import ArtifactPathResolver, ResolveArtifactLocationRequest
from datp_core.infrastructure.persistence.roots import bind_storage_root

_ARTIFACT_ID = ArtifactId(value="artifact-" + "a" * 64)
_STAGE = StageFingerprint(value="b" * 64)


def _store(path: Path) -> FileArtifactStore:
    return FileArtifactStore(
        root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.TEST_SANDBOX, visibility=StorageVisibility.TEST_ISOLATED),
            absolute_path=path,
        )
    )


def _key() -> RunArtifactKey:
    return RunArtifactKey(
        artifact_type=ArtifactType.RESULT_FREEZE,
        stage_identity=_STAGE,
        namespace=ArtifactNamespace.TEST_SANDBOX,
    )


def _request(
    content: bytes,
    *,
    disposition: WriteDisposition = WriteDisposition.ATOMIC_STAGE_COMMIT,
    schema_version: str = "v1",
) -> WriteArtifactRequest:
    return WriteArtifactRequest(
        key=_key(),
        artifact=ArtifactRef(
            artifact_id=_ARTIFACT_ID,
            artifact_type=ArtifactType.RESULT_FREEZE,
            content_hash=blake3_bytes_content_hash(content),
            schema_version=ArtifactSchemaVersion(value=schema_version),
            serialization_format=SerializationFormat.JSON,
        ),
        content=content,
        write_disposition=disposition,
    )


def _path(store: FileArtifactStore, request: WriteArtifactRequest) -> Path:
    return (
        ArtifactPathResolver()
        .resolve(ResolveArtifactLocationRequest(key=request.key, root=store.root, artifact=request.artifact))
        .absolute_path
    )


def test_adapter_implements_exactly_the_single_artifact_store_methods() -> None:
    methods = tuple(
        name for name, member in FileArtifactStore.__dict__.items() if callable(member) and not name.startswith("_")
    )
    assert methods == ("lookup", "write_atomically", "validate_integrity")
    for name in methods:
        assert signature(getattr(FileArtifactStore, name)) == signature(getattr(ArtifactStore, name))


def test_same_logical_id_with_different_content_raises_typed_integrity_error(tmp_path: Path) -> None:
    store = _store(tmp_path)
    original = _request(b"synthetic original")
    store.write_atomically(original)
    replacement = _request(b"synthetic replacement")

    with pytest.raises(ArtifactError):
        store.write_atomically(replacement)

    validation = store.validate_integrity(ValidateArtifactRequest(key=original.key, artifact=original.artifact))
    assert validation.status.value == "valid"


def test_integrity_validation_reports_an_incompatible_persisted_schema(tmp_path: Path) -> None:
    store = _store(tmp_path)
    persisted = _request(b"synthetic schema evidence")
    store.write_atomically(persisted)
    requested = _request(b"synthetic schema evidence", schema_version="v2")

    validation = store.validate_integrity(ValidateArtifactRequest(key=requested.key, artifact=requested.artifact))

    assert validation.integrity is IntegrityStatus.INTACT
    assert validation.schema_compatibility is SchemaCompatibility.INCOMPATIBLE


def test_interrupted_replace_leaves_no_completed_artifact_or_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    request = _request(b"synthetic interrupted artifact")

    def interrupted_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("simulated process interruption before replace")

    monkeypatch.setattr("datp_core.infrastructure.persistence.artifacts.replace", interrupted_replace)

    with pytest.raises(PartialArtifactError):
        store.write_atomically(request)

    assert not _path(store, request).exists()
    assert (
        store.lookup(ArtifactLookupRequest(artifact_id=request.artifact.artifact_id, key=request.key)).artifact is None
    )
    assert not tuple(tmp_path.rglob(".artifact-*"))


def test_manifest_replace_follows_content_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(tmp_path)
    request = _request(b"synthetic ordering evidence")
    replacements: list[tuple[Path, Path]] = []
    from os import replace as os_replace

    def record_replace(source: str | Path, destination: str | Path) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        replacements.append((source_path, destination_path))
        os_replace(source_path, destination_path)

    monkeypatch.setattr("datp_core.infrastructure.persistence.artifacts.replace", record_replace)
    store.write_atomically(request)

    assert tuple(source.name.startswith(".artifact-") for source, _ in replacements) == (True, False)
    assert tuple(source.name.startswith(".manifest-") for source, _ in replacements) == (False, True)
    assert replacements[0][1] == _path(store, request)


def test_verify_or_fail_never_creates_an_absent_artifact(tmp_path: Path) -> None:
    store = _store(tmp_path)
    request = _request(b"synthetic verification", disposition=WriteDisposition.VERIFY_OR_FAIL)

    with pytest.raises(ArtifactError):
        store.write_atomically(request)

    assert not _path(store, request).exists()
