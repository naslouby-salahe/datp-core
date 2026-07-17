from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, FeatureSchemaIdentity
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.errors import DomainValidationError


class Dataset(StrEnum):
    N_BAIOT = "n_baiot"
    CICIOT2023 = "ciciot2023"
    EDGE_IIOTSET = "edge_iiotset"


class Regime(StrEnum):
    A = "a"
    B_A = "b_a"
    C = "c"
    D = "d"
    D_TEMPORAL = "d_temporal"


class TimestampEvidenceKind(StrEnum):
    GENUINE_CAPTURE_TIME = "genuine_capture_time"


def _validated_timestamp_field(value: str) -> None:
    if not value:
        raise DomainValidationError(
            detail="capture timestamp evidence requires a field name", value=repr(value), constraint="non-empty"
        )
    if any(character.isspace() for character in value):
        raise DomainValidationError(
            detail="capture timestamp evidence must not contain whitespace",
            value=repr(value),
            constraint="no whitespace",
        )
    _validated_not_pseudo_time(value)


def _validated_not_pseudo_time(value: str) -> None:
    if any(marker in value.casefold() for marker in ("file", "row", "merge", "directory", "synthetic", "order")):
        raise DomainValidationError(
            detail="timestamp evidence must name genuine capture time",
            value=repr(value),
            constraint="genuine capture-time field",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetSpec:
    dataset: Dataset
    input_dim: int
    feature_schema_identity: FeatureSchemaIdentity
    feature_count_verified: bool

    def __post_init__(self) -> None:
        if isinstance(self.input_dim, bool) or self.input_dim < 1:
            raise DomainValidationError(
                detail="dataset input dimension must be a positive integer",
                value=repr(self.input_dim),
                constraint="input dimension >= 1",
            )
        if self.dataset is Dataset.CICIOT2023 and not self.feature_count_verified:
            raise DomainValidationError(
                detail="CICIoT2023 requires verified feature count",
                value=repr(self.feature_count_verified),
                constraint="CICIoT2023 feature count verified",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TimestampEvidence:
    kind: TimestampEvidenceKind
    capture_timestamp_field: str

    def __post_init__(self) -> None:
        if self.kind is not TimestampEvidenceKind.GENUINE_CAPTURE_TIME:
            raise DomainValidationError(
                detail="timestamp evidence must be classified as genuine capture time",
                value=repr(self.kind),
                constraint="GENUINE_CAPTURE_TIME",
            )
        _validated_timestamp_field(self.capture_timestamp_field)


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetSourceInspectionResult:
    source_manifest: ArtifactRef
    feature_schema_manifest: ArtifactRef
    source_row_identity: DatasetSourceIdentity
    timestamp_evidence: TimestampEvidence | None


def _validated_relative_path(value: str) -> None:
    if not value or value.startswith("/"):
        raise DomainValidationError(
            detail="source file manifest entry requires a non-empty relative path",
            value=repr(value),
            constraint="non-empty relative path",
        )


def _validated_device_id(value: str) -> None:
    if not value:
        raise DomainValidationError(
            detail="source file manifest entry requires a non-empty device id",
            value=repr(value),
            constraint="non-empty device id",
        )


def _validated_entry_row_count(value: int) -> None:
    if isinstance(value, bool) or value < 0:
        raise DomainValidationError(
            detail="source file manifest entry row count must be a non-negative integer",
            value=repr(value),
            constraint="row count >= 0",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceFileManifestEntry:
    relative_path: str
    device_id: str
    label: str
    row_count: int
    content_hash: str

    def __post_init__(self) -> None:
        _validated_relative_path(self.relative_path)
        _validated_device_id(self.device_id)
        _validated_entry_row_count(self.row_count)


def _validated_device_ids(device_ids: tuple[str, ...]) -> None:
    if not device_ids or len(set(device_ids)) != len(device_ids):
        raise DomainValidationError(
            detail="dataset source manifest requires at least one unique device id",
            value=repr(device_ids),
            constraint="non-empty unique device ids",
        )


def _validated_source_files_present(source_files: tuple[SourceFileManifestEntry, ...]) -> None:
    if not source_files:
        raise DomainValidationError(
            detail="dataset source manifest requires at least one source file entry",
            value=repr(source_files),
            constraint="non-empty source files",
        )


def _validated_unique_relative_paths(source_files: tuple[SourceFileManifestEntry, ...]) -> None:
    relative_paths = tuple(entry.relative_path for entry in source_files)
    if len(set(relative_paths)) != len(relative_paths):
        raise DomainValidationError(
            detail="dataset source manifest file paths must be unique",
            value=repr(relative_paths),
            constraint="unique relative paths",
        )


def _validated_known_devices(*, source_files: tuple[SourceFileManifestEntry, ...], device_ids: tuple[str, ...]) -> None:
    unknown_devices = {entry.device_id for entry in source_files} - set(device_ids)
    if unknown_devices:
        raise DomainValidationError(
            detail="dataset source manifest file entries reference an undeclared device id",
            value=repr(sorted(unknown_devices)),
            constraint="device id declared in device_ids",
        )


def _validated_total_row_count(*, total_row_count: int, source_files: tuple[SourceFileManifestEntry, ...]) -> None:
    if total_row_count != sum(entry.row_count for entry in source_files):
        raise DomainValidationError(
            detail="dataset source manifest total row count must equal the sum of its file entries",
            value=repr(total_row_count),
            constraint="total_row_count == sum(source_files.row_count)",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetSourceManifest:
    dataset: Dataset
    device_ids: tuple[str, ...]
    source_files: tuple[SourceFileManifestEntry, ...]
    total_row_count: int

    def __post_init__(self) -> None:
        _validated_device_ids(self.device_ids)
        _validated_source_files_present(self.source_files)
        _validated_unique_relative_paths(self.source_files)
        _validated_known_devices(source_files=self.source_files, device_ids=self.device_ids)
        _validated_total_row_count(total_row_count=self.total_row_count, source_files=self.source_files)


def _validated_feature_columns_present(feature_columns: tuple[str, ...]) -> None:
    if not feature_columns or len(set(feature_columns)) != len(feature_columns):
        raise DomainValidationError(
            detail="feature schema manifest requires at least one unique feature column",
            value=repr(feature_columns),
            constraint="non-empty unique feature columns",
        )


def _validated_input_dim_matches(*, input_dim: int, feature_columns: tuple[str, ...]) -> None:
    if input_dim != len(feature_columns):
        raise DomainValidationError(
            detail="feature schema manifest input dimension must equal the feature column count",
            value=repr(input_dim),
            constraint="input_dim == len(feature_columns)",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class FeatureSchemaManifest:
    dataset: Dataset
    feature_columns: tuple[str, ...]
    input_dim: int

    def __post_init__(self) -> None:
        _validated_feature_columns_present(self.feature_columns)
        _validated_input_dim_matches(input_dim=self.input_dim, feature_columns=self.feature_columns)
