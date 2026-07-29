"""Completion markers for reusable processed-data publications."""

from hashlib import sha256
from pathlib import Path

from datp_core.artifacts.layout import ProcessedAssetName
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values import Checksum


def complete_digest(manifest_payload: str, schema_payload: str) -> Checksum:
    digest = sha256()
    digest.update(manifest_payload.encode())
    digest.update(b"\n")
    digest.update(schema_payload.encode())
    return Checksum(digest.hexdigest())


def write_complete_marker(directory: Path, digest: Checksum) -> Path:
    path = directory / ProcessedAssetName.COMPLETE
    path.write_text(digest.value, encoding="utf-8")
    return path


def read_complete_marker(directory: Path) -> Checksum:
    path = directory / ProcessedAssetName.COMPLETE
    if not path.is_file():
        raise ArtifactIntegrityError("processed asset is missing COMPLETE marker", subject=str(directory))
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ArtifactIntegrityError("processed COMPLETE marker is empty", subject=str(directory))
    return Checksum(value)


def assert_complete_digest(directory: Path, expected: Checksum) -> None:
    actual = read_complete_marker(directory)
    if actual != expected:
        raise ArtifactIntegrityError("processed COMPLETE digest mismatch", subject=str(directory))
