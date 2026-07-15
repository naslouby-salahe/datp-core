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


class SourceTrafficLabel(StrEnum):
    BENIGN = "benign"
    GAFGYT = "gafgyt"
    MIRAI = "mirai"


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceFileManifestEntry:
    relative_path: str
    device_id: str
    label: SourceTrafficLabel
    row_count: int
    content_hash: str

    def __post_init__(self) -> None:
        if not self.relative_path or self.relative_path.startswith("/"):
            raise DomainValidationError(
                detail="source file manifest entry requires a non-empty relative path",
                value=repr(self.relative_path),
                constraint="non-empty relative path",
            )
        if not self.device_id:
            raise DomainValidationError(
                detail="source file manifest entry requires a non-empty device id",
                value=repr(self.device_id),
                constraint="non-empty device id",
            )
        if isinstance(self.row_count, bool) or self.row_count < 0:
            raise DomainValidationError(
                detail="source file manifest entry row count must be a non-negative integer",
                value=repr(self.row_count),
                constraint="row count >= 0",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetSourceManifest:
    dataset: Dataset
    device_ids: tuple[str, ...]
    source_files: tuple[SourceFileManifestEntry, ...]
    total_row_count: int

    def __post_init__(self) -> None:
        if not self.device_ids:
            raise DomainValidationError(
                detail="dataset source manifest requires at least one device id",
                value=repr(self.device_ids),
                constraint="non-empty device ids",
            )
        if len(set(self.device_ids)) != len(self.device_ids):
            raise DomainValidationError(
                detail="dataset source manifest device ids must be unique",
                value=repr(self.device_ids),
                constraint="unique device ids",
            )
        if not self.source_files:
            raise DomainValidationError(
                detail="dataset source manifest requires at least one source file entry",
                value=repr(self.source_files),
                constraint="non-empty source files",
            )
        relative_paths = tuple(entry.relative_path for entry in self.source_files)
        if len(set(relative_paths)) != len(relative_paths):
            raise DomainValidationError(
                detail="dataset source manifest file paths must be unique",
                value=repr(relative_paths),
                constraint="unique relative paths",
            )
        unknown_devices = set(entry.device_id for entry in self.source_files) - set(self.device_ids)
        if unknown_devices:
            raise DomainValidationError(
                detail="dataset source manifest file entries reference an undeclared device id",
                value=repr(sorted(unknown_devices)),
                constraint="device id declared in device_ids",
            )
        if self.total_row_count != sum(entry.row_count for entry in self.source_files):
            raise DomainValidationError(
                detail="dataset source manifest total row count must equal the sum of its file entries",
                value=repr(self.total_row_count),
                constraint="total_row_count == sum(source_files.row_count)",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FeatureSchemaManifest:
    dataset: Dataset
    feature_columns: tuple[str, ...]
    input_dim: int

    def __post_init__(self) -> None:
        if not self.feature_columns:
            raise DomainValidationError(
                detail="feature schema manifest requires at least one feature column",
                value=repr(self.feature_columns),
                constraint="non-empty feature columns",
            )
        if len(set(self.feature_columns)) != len(self.feature_columns):
            raise DomainValidationError(
                detail="feature schema manifest feature columns must be unique",
                value=repr(self.feature_columns),
                constraint="unique feature columns",
            )
        if self.input_dim != len(self.feature_columns):
            raise DomainValidationError(
                detail="feature schema manifest input dimension must equal the feature column count",
                value=repr(self.input_dim),
                constraint="input_dim == len(feature_columns)",
            )
