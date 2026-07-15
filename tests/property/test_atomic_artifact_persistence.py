from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st

from datp_core.application.ports.persistence import WriteArtifactRequest
from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    RunArtifactKey,
    SerializationFormat,
    StorageRootKind,
    StorageRootSpec,
    StorageVisibility,
    WriteDisposition,
)
from datp_core.domain.artifacts.lineage import StageFingerprint
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion
from datp_core.infrastructure.persistence.artifacts import FileArtifactStore
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash
from datp_core.infrastructure.persistence.paths import ArtifactPathResolver, ResolveArtifactLocationRequest
from datp_core.infrastructure.persistence.roots import bind_storage_root


@given(st.binary(max_size=4096))
def test_identical_atomic_writes_are_deduplicated_without_rechecking_persisted_content(content: bytes) -> None:
    artifact = ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + "c" * 64),
        artifact_type=ArtifactType.RESULT_FREEZE,
        content_hash=blake3_bytes_content_hash(content),
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )
    key = RunArtifactKey(
        artifact_type=ArtifactType.RESULT_FREEZE,
        stage_identity=StageFingerprint(value="d" * 64),
        namespace=ArtifactNamespace.TEST_SANDBOX,
    )
    request = WriteArtifactRequest(
        key=key,
        artifact=artifact,
        content=content,
        write_disposition=WriteDisposition.ATOMIC_STAGE_COMMIT,
    )
    with TemporaryDirectory() as directory:
        store = FileArtifactStore(
            root=bind_storage_root(
                spec=StorageRootSpec(kind=StorageRootKind.TEST_SANDBOX, visibility=StorageVisibility.TEST_ISOLATED),
                absolute_path=Path(directory),
            )
        )
        store.write_atomically(request)
        persisted_path = (
            ArtifactPathResolver()
            .resolve(ResolveArtifactLocationRequest(key=key, root=store.root, artifact=artifact))
            .absolute_path
        )
        before = persisted_path.stat()
        with patch("datp_core.infrastructure.persistence.artifacts.blake3_file_content_hash") as persisted_hash:
            store.write_atomically(request)

        assert persisted_path.stat().st_ino == before.st_ino
        persisted_hash.assert_not_called()
