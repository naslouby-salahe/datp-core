from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.runtime.policies import PipelineStage


class LockScope(StrEnum):
    COMPUTATION_OWNERSHIP = "computation_ownership"
    COMMIT = "commit"


class ValidationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    UNVERIFIED = "unverified"


_ARTIFACT_ID_PATTERN = r"artifact-[0-9a-f]{64}"
_RUN_IDENTITY_PATTERN = r"run-[0-9a-f]{64}"
_CHECKPOINT_ID_PATTERN = r"checkpoint-[0-9a-f]{64}"
_STAGE_FINGERPRINT_PATTERN = r"[0-9a-f]{64}"
_CONTENT_HASH_PATTERN = r"[0-9a-f]{64}"


def _validated_identity(*, value: str, pattern: str, name: str) -> str:
    if fullmatch(pattern, value) is None:
        raise DomainValidationError(
            detail=f"{name} has an invalid canonical format",
            value=value,
            constraint=pattern,
        )
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactId:
    value: str

    def __post_init__(self) -> None:
        _validated_identity(value=self.value, pattern=_ARTIFACT_ID_PATTERN, name="artifact id")


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationScoreArtifactId:
    value: str

    def __post_init__(self) -> None:
        _validated_identity(
            value=self.value,
            pattern=_ARTIFACT_ID_PATTERN,
            name="calibration score artifact id",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class TestScoreArtifactId:
    value: str

    def __post_init__(self) -> None:
        _validated_identity(value=self.value, pattern=_ARTIFACT_ID_PATTERN, name="test score artifact id")


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalScoreArtifactId:
    value: str

    def __post_init__(self) -> None:
        _validated_identity(value=self.value, pattern=_ARTIFACT_ID_PATTERN, name="temporal score artifact id")


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactSchemaVersion:
    value: str

    def __post_init__(self) -> None:
        if not self.value or any(character.isspace() for character in self.value):
            raise DomainValidationError(
                detail="artifact schema version must be non-empty and contain no whitespace",
                value=repr(self.value),
                constraint="non-empty schema version without whitespace",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactRef:
    artifact_id: ArtifactId
    artifact_type: ArtifactType
    content_hash: str
    schema_version: ArtifactSchemaVersion
    serialization_format: SerializationFormat

    def __post_init__(self) -> None:
        _validated_identity(value=self.content_hash, pattern=_CONTENT_HASH_PATTERN, name="artifact content hash")


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactReferenceCollection:
    references: tuple[ArtifactRef, ...]

    def __post_init__(self) -> None:
        keys = tuple((reference.artifact_id.value, reference.content_hash) for reference in self.references)
        if len(set(keys)) != len(keys):
            raise DomainValidationError(
                detail="artifact references must be unique by artifact id and content hash",
                value=repr(keys),
                constraint="unique ordered artifact references",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class RunIdentity:
    value: str

    def __post_init__(self) -> None:
        _validated_identity(value=self.value, pattern=_RUN_IDENTITY_PATTERN, name="run identity")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionAttemptId:
    value: str

    def __post_init__(self) -> None:
        try:
            parsed = UUID(self.value.removeprefix("attempt-"))
        except ValueError as error:
            raise DomainValidationError(
                detail="execution attempt id must contain a UUID4",
                value=self.value,
                constraint="attempt-<uuid4>",
            ) from error
        if not self.value.startswith("attempt-") or parsed.version != 4 or str(parsed) != self.value[8:]:
            raise DomainValidationError(
                detail="execution attempt id must contain a canonical UUID4",
                value=self.value,
                constraint="attempt-<uuid4>",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointId:
    value: str

    def __post_init__(self) -> None:
        _validated_identity(value=self.value, pattern=_CHECKPOINT_ID_PATTERN, name="checkpoint id")


@dataclass(frozen=True, slots=True, kw_only=True)
class StageFingerprint:
    value: str

    def __post_init__(self) -> None:
        _validated_identity(value=self.value, pattern=_STAGE_FINGERPRINT_PATTERN, name="stage fingerprint")


@dataclass(frozen=True, slots=True, kw_only=True)
class StageRunIdentity:
    run_identity: RunIdentity
    execution_attempt_id: ExecutionAttemptId
    stage: PipelineStage
    stage_fingerprint: StageFingerprint
