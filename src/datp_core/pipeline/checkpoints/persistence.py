"""Shared persisted-checkpoint path and integrity services."""

from pathlib import Path

from datp_core.domain.enums import ContractSubject, SerializationFormat
from datp_core.domain.errors import ArtifactIntegrityError
from datp_core.domain.values import Checksum, checksum_file


def validate_persisted_checkpoint_file(
    path: Path,
    checksum: Checksum,
    *,
    serialization_format: SerializationFormat = SerializationFormat.SAFETENSORS,
) -> None:
    """Validate one checkpoint without loading branch-specific model state."""
    if not path.is_file():
        raise ArtifactIntegrityError(
            "checkpoint candidate tensor file is missing",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if checksum_file(path) != checksum:
        raise ArtifactIntegrityError(
            "checkpoint candidate checksum mismatch",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    if path.suffix != f".{serialization_format.value}":
        raise ArtifactIntegrityError(
            f"checkpoint must use {serialization_format.value} serialization",
            subject=ContractSubject.ARTIFACT_PATH,
        )
