from datp_core.domain.enums import ContractSubject
"""Completion markers for reusable processed-data publications."""

from pathlib import Path

from datp_core.artifacts.layout import ProcessedAssetName
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values import Checksum, checksum_text


def complete_digest(manifest_payload: str, schema_payload: str) -> Checksum:
    return checksum_text(f"{manifest_payload}\n{schema_payload}")


def write_complete_marker(directory: Path, digest: Checksum) -> Path:
    path = directory / ProcessedAssetName.COMPLETE
    path.write_text(digest.value, encoding="utf-8")
    return path


def read_complete_marker(directory: Path) -> Checksum:
    path = directory / ProcessedAssetName.COMPLETE
    if not path.is_file():
        raise ArtifactIntegrityError("processed asset is missing COMPLETE marker", subject=ContractSubject.ARTIFACT_PATH)
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ArtifactIntegrityError("processed COMPLETE marker is empty", subject=ContractSubject.ARTIFACT_PATH)
    return Checksum(value)


def assert_complete_digest(directory: Path, expected: Checksum) -> None:
    actual = read_complete_marker(directory)
    if actual != expected:
        raise ArtifactIntegrityError("processed COMPLETE digest mismatch", subject=ContractSubject.ARTIFACT_PATH)
