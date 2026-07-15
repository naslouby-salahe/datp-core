from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import match, split
from typing import TYPE_CHECKING
from urllib.parse import unquote

from datp_core.domain.errors import DomainValidationError

if TYPE_CHECKING:
    from datp_core.domain.artifacts.lineage import StageFingerprint
    from datp_core.domain.artifacts.manifests import ArtifactType
    from datp_core.domain.data.datasets import Dataset, Regime
    from datp_core.domain.runtime.seeds import Seed


class StorageRootKind(StrEnum):
    RAW_DATA = "raw_data"
    PROCESSED_DATA = "processed_data"
    SCIENTIFIC_CHECKPOINTS = "scientific_checkpoints"
    RECOVERY_STATE = "recovery_state"
    SCORES = "scores"
    METRICS = "metrics"
    STATISTICS = "statistics"
    REPORTS = "reports"
    RUN_STATE = "run_state"
    CACHE = "cache"
    LOCKS = "locks"
    STAGING = "staging"
    TEST_SANDBOX = "test_sandbox"


class StorageVisibility(StrEnum):
    EXTERNAL_READONLY = "external_readonly"
    SCIENTIFIC_OUTPUT = "scientific_output"
    EPHEMERAL = "ephemeral"
    TEST_ISOLATED = "test_isolated"


class ArtifactNamespace(StrEnum):
    DATP_ANCHOR = "datp_anchor"
    JOURNAL_EXTENSION = "journal_extension"
    RECOVERY = "recovery"
    CACHE = "cache"
    STAGING = "staging"
    TEST_SANDBOX = "test_sandbox"


class SerializationFormat(StrEnum):
    PARQUET = "parquet"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    LATEX = "latex"
    SVG = "svg"
    PNG = "png"
    PDF = "pdf"
    TORCH_STATE = "torch_state"


class WriteDisposition(StrEnum):
    CREATE_IF_ABSENT = "create_if_absent"
    VERIFY_OR_FAIL = "verify_or_fail"
    ATOMIC_STAGE_COMMIT = "atomic_stage_commit"


class ArtifactRetentionPolicy(StrEnum):
    DISCARD_ON_SUCCESS = "discard_on_success"
    RETAIN_ON_FAILURE = "retain_on_failure"
    RETAIN_ALWAYS = "retain_always"
    EPHEMERAL = "ephemeral"


@dataclass(frozen=True, slots=True, kw_only=True)
class StorageRootSpec:
    kind: StorageRootKind
    visibility: StorageVisibility

    def __post_init__(self) -> None:
        if type(self.kind) is not StorageRootKind or type(self.visibility) is not StorageVisibility:
            raise DomainValidationError(
                detail="storage root specification requires typed kind and visibility",
                value=repr(self),
                constraint="StorageRootKind and StorageVisibility",
            )
        if self.visibility is not _expected_visibility(self.kind):
            raise DomainValidationError(
                detail="storage root visibility must match its semantic root kind",
                value=repr(self),
                constraint=_expected_visibility(self.kind).value,
            )


def _expected_visibility(kind: StorageRootKind) -> StorageVisibility:
    if kind is StorageRootKind.RAW_DATA:
        return StorageVisibility.EXTERNAL_READONLY
    if kind in {
        StorageRootKind.PROCESSED_DATA,
        StorageRootKind.SCIENTIFIC_CHECKPOINTS,
        StorageRootKind.SCORES,
        StorageRootKind.METRICS,
        StorageRootKind.STATISTICS,
        StorageRootKind.REPORTS,
    }:
        return StorageVisibility.SCIENTIFIC_OUTPUT
    if kind is StorageRootKind.TEST_SANDBOX:
        return StorageVisibility.TEST_ISOLATED
    return StorageVisibility.EPHEMERAL


def _validated_nonnegative_integer(*, value: object, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainValidationError(detail=f"{name} must be an integer", value=repr(value), constraint="integer")
    if value < 0:
        raise DomainValidationError(
            detail=f"{name} must be a non-negative integer",
            value=repr(value),
            constraint="integer >= 0",
        )


def _decoded_path_variants(value: str) -> tuple[str, ...]:
    variants = [value]
    decoded_value = value
    for _ in range(16):
        next_value = unquote(decoded_value)
        if next_value == decoded_value:
            break
        variants.append(next_value)
        decoded_value = next_value
    return tuple(variants)


def _validated_relative_path(value: object) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise DomainValidationError(detail="artifact path must be a string", value=repr(value), constraint="string")
    if not value:
        raise DomainValidationError(
            detail="artifact path must be non-empty", value=repr(value), constraint="non-empty path"
        )
    if any(character.isspace() for character in value):
        raise DomainValidationError(
            detail="artifact path must be non-empty and contain no whitespace",
            value=repr(value),
            constraint="non-empty path without whitespace",
        )
    return _decoded_path_variants(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class ByteCount:
    value: int

    def __post_init__(self) -> None:
        _validated_nonnegative_integer(value=self.value, name="byte count")


@dataclass(frozen=True, slots=True, kw_only=True)
class DiskCapacity:
    value: int

    def __post_init__(self) -> None:
        _validated_nonnegative_integer(value=self.value, name="disk capacity")


@dataclass(frozen=True, slots=True, kw_only=True)
class RelativeArtifactPath:
    value: str

    def __post_init__(self) -> None:
        for candidate in _validated_relative_path(self.value):
            _validated_path_candidate(candidate=candidate, original_value=self.value)


def _validated_path_candidate(*, candidate: str, original_value: str) -> None:
    _validated_candidate_whitespace(candidate=candidate, original_value=original_value)
    _validated_candidate_root(candidate=candidate, original_value=original_value)
    _validated_candidate_traversal(candidate=candidate, original_value=original_value)


def _validated_candidate_whitespace(*, candidate: str, original_value: str) -> None:
    if any(character.isspace() for character in candidate):
        raise DomainValidationError(
            detail="artifact path must not encode whitespace",
            value=original_value,
            constraint="path without whitespace",
        )


def _validated_candidate_root(*, candidate: str, original_value: str) -> None:
    if candidate.startswith(("/", "\\")) or match(r"^[A-Za-z]:", candidate):
        raise DomainValidationError(
            detail="artifact path must be relative and must not use a drive letter",
            value=original_value,
            constraint="POSIX relative path without drive letter",
        )


def _validated_candidate_traversal(*, candidate: str, original_value: str) -> None:
    if "\\" in candidate or ".." in split(r"[\\/]", candidate):
        raise DomainValidationError(
            detail="artifact path must not contain a parent traversal component",
            value=original_value,
            constraint="path without parent traversal",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetArtifactKey:
    artifact_type: ArtifactType
    dataset: Dataset
    stage_identity: StageFingerprint
    namespace: ArtifactNamespace


@dataclass(frozen=True, slots=True, kw_only=True)
class RegimeArtifactKey:
    artifact_type: ArtifactType
    dataset: Dataset
    regime: Regime
    stage_identity: StageFingerprint
    namespace: ArtifactNamespace


@dataclass(frozen=True, slots=True, kw_only=True)
class SeedScopedArtifactKey:
    artifact_type: ArtifactType
    dataset: Dataset
    regime: Regime
    seed: Seed
    stage_identity: StageFingerprint
    namespace: ArtifactNamespace


@dataclass(frozen=True, slots=True, kw_only=True)
class CrossSeedArtifactKey:
    artifact_type: ArtifactType
    dataset: Dataset
    regime: Regime
    seed_cohort_identity: StageFingerprint
    stage_identity: StageFingerprint
    namespace: ArtifactNamespace


@dataclass(frozen=True, slots=True, kw_only=True)
class RunArtifactKey:
    artifact_type: ArtifactType
    stage_identity: StageFingerprint
    namespace: ArtifactNamespace


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportArtifactKey:
    artifact_type: ArtifactType
    stage_identity: StageFingerprint
    namespace: ArtifactNamespace


type ArtifactKey = (
    DatasetArtifactKey
    | RegimeArtifactKey
    | SeedScopedArtifactKey
    | CrossSeedArtifactKey
    | RunArtifactKey
    | ReportArtifactKey
)
