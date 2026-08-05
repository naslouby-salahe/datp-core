"""Pipeline checkpoint persistence validation."""

from pathlib import Path

from datp_core.domain.enums import SerializationFormat
from datp_core.domain.values import Checksum
from datp_core.protocols.checkpoints import validate_persisted_checkpoint_file as validate_checkpoint_file


def validate_persisted_checkpoint_file(
    path: Path,
    checksum: Checksum,
    *,
    serialization_format: SerializationFormat = SerializationFormat.SAFETENSORS,
) -> None:
    validate_checkpoint_file(path, checksum, serialization_format=serialization_format)
