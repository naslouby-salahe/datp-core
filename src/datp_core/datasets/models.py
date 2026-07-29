"""Immutable records for audited dataset ingestion and publication."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.domain.enums import AvailabilityStatus, DatasetId
from datp_core.domain.values import ByteCount, Checksum


class SourceFileRole(StrEnum):
    BENIGN = "benign"
    ATTACK = "attack"
    MERGED = "merged"
    DOCUMENTATION = "documentation"
    ARCHIVE = "archive"
    SELECTED_REPRESENTATION = "selected_representation"
    CHRONOLOGY_EVIDENCE = "chronology_evidence"


class CanonicalColumnRole(StrEnum):
    FEATURE = "feature"
    LABEL = "label"
    PROVENANCE = "provenance"
    IDENTITY = "identity"
    RAW_EVIDENCE = "raw_evidence"


class ColumnLogicalType(StrEnum):
    FLOAT64 = "float64"
    UINT64 = "uint64"
    STRING = "string"
    BOOL = "bool"
    TIMESTAMP_NS_UTC = "timestamp[ns, tz=UTC]"


class DatasetValidationCode(StrEnum):
    UNRECOGNIZED_OR_EMPTY_LABEL = "unrecognized_or_empty_label"
    INFINITE_RATE = "infinite_rate"
    NONFINITE_MODEL_INPUT_FEATURE = "nonfinite_model_input_feature"
    EMPTY_RATE = "empty_rate"
    INVALID_CHRONOLOGY = "invalid_chronology"
    NONFINITE_FEATURE_VALUES = "nonfinite_feature_values"
    TEMPORAL_CHRONOLOGY_UNAVAILABLE = "temporal_chronology_unavailable"


class AggregateCountColumn(StrEnum):
    TOTAL_ROWS = "total_rows"
    INVALID_ROWS = "invalid_rows"
    INVALID = "invalid"


class CanonicalProvenanceColumn(StrEnum):
    SOURCE_ROW_INDEX = "source_row_index"
    SOURCE_PATH = "source_path"
    STABLE_ROW_ID = "stable_row_id"


class CanonicalPublicationArtifact(StrEnum):
    COMPLETE = "COMPLETE"
    MANIFEST = "dataset_manifest.json"
    SCHEMA = "schema.json"
    SOURCE_STATE = "source_state.json"


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ExclusionReason(StrEnum):
    UNRECOGNIZED_SOURCE = "unrecognized_source"
    INVALID_SCHEMA = "invalid_schema"
    INVALID_VALUE = "invalid_value"
    INVALID_CHRONOLOGY = "invalid_chronology"


class PublicationStatus(StrEnum):
    PUBLISHED = "published"
    REUSED = "reused"


class CanonicalAssetRole(StrEnum):
    CANONICAL_DATA = "canonical_data"


@dataclass(frozen=True, slots=True)
class RawSourceFile:
    dataset: DatasetId
    relative_path: Path
    size_bytes: ByteCount
    checksum: Checksum
    role: SourceFileRole
    observed_row_count: int | None

    def __post_init__(self) -> None:
        if self.relative_path.is_absolute():
            raise ValueError("raw source paths must be relative")
        if self.observed_row_count is not None and self.observed_row_count < 0:
            raise ValueError("observed row count must be non-negative")


@dataclass(frozen=True, slots=True)
class RawDatasetInventory:
    dataset: DatasetId
    sources: tuple[RawSourceFile, ...]
    accepted_source_count: int
    excluded_source_count: int
    accepted_row_count: int | None
    checksum: Checksum

    def __post_init__(self) -> None:
        _validate_inventory_sources(self.sources, self.accepted_source_count)
        _validate_inventory_counts(self.excluded_source_count, self.accepted_row_count)


@dataclass(frozen=True, slots=True)
class CanonicalColumn:
    name: str
    source_name: str
    dtype: ColumnLogicalType
    role: CanonicalColumnRole
    nullable: bool
    position: int

    def __post_init__(self) -> None:
        if not self.name or not self.source_name:
            raise ValueError("canonical columns require non-empty names")
        if not isinstance(self.dtype, ColumnLogicalType):
            raise ValueError("canonical columns require a ColumnLogicalType dtype")
        if self.position < 0:
            raise ValueError("canonical column positions must be non-negative")


@dataclass(frozen=True, slots=True)
class CanonicalSchema:
    dataset: DatasetId
    columns: tuple[CanonicalColumn, ...]
    feature_columns: tuple[str, ...]
    label_columns: tuple[str, ...]
    provenance_columns: tuple[str, ...]
    physical_schema: str
    checksum: Checksum

    def __post_init__(self) -> None:
        _validate_canonical_columns(self.columns, self.physical_schema)
        _validate_declared_columns(self.columns, self.feature_columns, CanonicalColumnRole.FEATURE, "feature")
        _validate_declared_columns(self.columns, self.label_columns, CanonicalColumnRole.LABEL, "label")
        _validate_declared_columns(self.columns, self.provenance_columns, CanonicalColumnRole.PROVENANCE, "provenance")


@dataclass(frozen=True, slots=True)
class SourceRowReference:
    source: RawSourceFile
    zero_based_row_index: int

    def __post_init__(self) -> None:
        if self.zero_based_row_index < 0:
            raise ValueError("source row indexes are zero-based and non-negative")


@dataclass(frozen=True, slots=True)
class DatasetRowIdentity:
    dataset: DatasetId
    source_row: SourceRowReference
    stable_id: str

    def __post_init__(self) -> None:
        if not self.stable_id:
            raise ValueError("stable row identities must be non-empty")


@dataclass(frozen=True, slots=True)
class DatasetExclusion:
    dataset: DatasetId
    source_path: Path | None
    source_row: SourceRowReference | None
    reason: ExclusionReason
    evidence: str
    affected_count: int

    def __post_init__(self) -> None:
        if self.source_path is None and self.source_row is None:
            raise ValueError("an exclusion requires source context")
        if not self.evidence or self.affected_count < 1:
            raise ValueError("exclusions require evidence and a positive affected count")


@dataclass(frozen=True, slots=True)
class DatasetValidationIssue:
    severity: ValidationSeverity
    code: DatasetValidationCode
    dataset: DatasetId
    source_context: str
    reason: str
    affected_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.code, DatasetValidationCode):
            raise ValueError("validation issues require a DatasetValidationCode")
        if not self.source_context or not self.reason or self.affected_count < 1:
            raise ValueError("validation issues require complete source evidence")


@dataclass(frozen=True, slots=True)
class DatasetValidationReport:
    dataset: DatasetId
    issues: tuple[DatasetValidationIssue, ...]
    exclusions: tuple[DatasetExclusion, ...]
    accepted_rows: int
    excluded_rows: int
    invalid_rows: int
    warning_count: int
    status: AvailabilityStatus

    def __post_init__(self) -> None:
        _validate_report_collections(self.issues, self.exclusions)
        _validate_non_negative_counts(self.accepted_rows, self.excluded_rows, self.invalid_rows, self.warning_count)
        if self.warning_count != _warning_count(self.issues):
            raise ValueError("warning count must match warning issues")
        if self.excluded_rows != _excluded_row_count(self.exclusions):
            raise ValueError("excluded rows must match recorded exclusions")


@dataclass(frozen=True, slots=True)
class ModelInputEligibilityPolicy[EligibilityReasonT: StrEnum]:
    dataset: DatasetId
    label_column: str
    feature_columns: tuple[str, ...]
    exclusion_reasons: tuple[EligibilityReasonT, ...]

    def __post_init__(self) -> None:
        if not self.label_column or not self.feature_columns:
            raise ValueError("model-input eligibility policies require label and feature columns")
        if len(self.feature_columns) != len(frozenset(self.feature_columns)):
            raise ValueError("model-input eligibility feature columns must be unique")
        if len(self.exclusion_reasons) != len(frozenset(self.exclusion_reasons)):
            raise ValueError("model-input eligibility reasons must be unique")


def _validate_canonical_columns(columns: tuple[CanonicalColumn, ...], physical_schema: str) -> None:
    _require_schema_content(columns, physical_schema)
    _validate_column_order_and_names(columns)


def _require_schema_content(columns: tuple[CanonicalColumn, ...], physical_schema: str) -> None:
    if not columns:
        raise ValueError("canonical schemas require columns")
    if not physical_schema:
        raise ValueError("canonical schemas require an exact physical schema")


def _validate_column_order_and_names(columns: tuple[CanonicalColumn, ...]) -> None:
    if tuple(column.position for column in columns) != tuple(range(len(columns))):
        raise ValueError("canonical column positions must be contiguous and ordered")
    names = tuple(column.name for column in columns)
    if len(names) != len(frozenset(names)):
        raise ValueError("canonical column names must be unique")


def _validate_declared_columns(
    columns: tuple[CanonicalColumn, ...],
    declared: tuple[str, ...],
    role: CanonicalColumnRole,
    subject: str,
) -> None:
    names = tuple(column.name for column in columns if column.role is role)
    if names != declared:
        raise ValueError(f"{subject} columns must match ordered canonical {subject} declarations")


def _validate_inventory_sources(sources: tuple[RawSourceFile, ...], accepted_source_count: int) -> None:
    if not isinstance(sources, tuple):
        raise TypeError("sources must be an immutable tuple")
    if accepted_source_count != len(sources):
        raise ValueError("accepted source count must equal source tuple length")
    relative_paths = tuple(source.relative_path for source in sources)
    if len(relative_paths) != len(frozenset(relative_paths)):
        raise ValueError("raw inventory source paths must be unique")


def _validate_inventory_counts(excluded_source_count: int, accepted_row_count: int | None) -> None:
    if excluded_source_count < 0:
        raise ValueError("excluded source count must be non-negative")
    if accepted_row_count is not None and accepted_row_count < 0:
        raise ValueError("accepted row count must be non-negative")


def _validate_report_collections(
    issues: tuple[DatasetValidationIssue, ...], exclusions: tuple[DatasetExclusion, ...]
) -> None:
    if not isinstance(issues, tuple):
        raise TypeError("validation issues must be an immutable tuple")
    if not isinstance(exclusions, tuple):
        raise TypeError("dataset exclusions must be an immutable tuple")


def _validate_non_negative_counts(*counts: int) -> None:
    if min(counts) < 0:
        raise ValueError("validation counts must be non-negative")


def _warning_count(issues: tuple[DatasetValidationIssue, ...]) -> int:
    return sum(issue.severity is ValidationSeverity.WARNING for issue in issues)


def _excluded_row_count(exclusions: tuple[DatasetExclusion, ...]) -> int:
    return sum(exclusion.affected_count for exclusion in exclusions)


@dataclass(frozen=True, slots=True)
class MaterializedCanonicalAsset[AssetRoleT: StrEnum]:
    path: Path
    role: AssetRoleT
    row_count: int
    source_identity: str | None = None

    def __post_init__(self) -> None:
        if not self.path.is_absolute() or self.row_count < 0:
            raise ValueError("materialized canonical assets require an absolute path and non-negative row count")


@dataclass(frozen=True, slots=True)
class MaterializedDataset[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum]:
    dataset: DatasetId
    canonical_root: Path
    assets: tuple[MaterializedCanonicalAsset[AssetRoleT], ...]
    manifest_path: Path
    schema: CanonicalSchema
    row_count: int
    source_inventory_checksum: Checksum
    publication_status: PublicationStatus
    inventory: RawDatasetInventory
    validation_report: DatasetValidationReport
    chronology: tuple["ChronologyValidation", ...] = ()
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.assets, tuple) or not self.assets:
            raise ValueError("materialized datasets require immutable canonical assets")
        if self.row_count < 0:
            raise ValueError("materialized row count must be non-negative")


@dataclass(frozen=True, slots=True)
class ChronologyValidation:
    group_identity: str
    status: AvailabilityStatus
    total_rows: int
    parseable_rows: int
    invalid_rows: int
    duplicate_timestamp_count: int
    is_monotonic: bool
    reason: str
    temporal_eligible: bool
    evidence_source_path: Path | None = None
    evidence_row_count: int | None = None
    alignment_verified: bool = False
    alignment_offset_microseconds: int | None = None
    skipped_evidence_rows: int = 0
    trailing_evidence_rows: int = 0

    def __post_init__(self) -> None:
        _validate_chronology_identity(self)
        _validate_chronology_evidence(self)
        _validate_chronology_counts(self)


def _validate_chronology_identity(validation: ChronologyValidation) -> None:
    if not validation.group_identity or not validation.reason:
        raise ValueError("chronology validations require identity and reason")


def _validate_chronology_evidence(validation: ChronologyValidation) -> None:
    _validate_evidence_counts(validation)
    _validate_verified_evidence(validation)
    _validate_evidence_path(validation)


def _validate_evidence_counts(validation: ChronologyValidation) -> None:
    _validate_optional_non_negative(validation.evidence_row_count, "chronology evidence row counts")
    _validate_optional_non_negative(validation.alignment_offset_microseconds, "chronology alignment offsets")
    _validate_non_negative_pair(
        validation.skipped_evidence_rows,
        validation.trailing_evidence_rows,
        "skipped and trailing chronology evidence rows",
    )


def _validate_optional_non_negative(value: int | None, subject: str) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{subject} must be non-negative")


def _validate_non_negative_pair(first: int, second: int, subject: str) -> None:
    if min(first, second) < 0:
        raise ValueError(f"{subject} must be non-negative")


def _validate_verified_evidence(validation: ChronologyValidation) -> None:
    verified_evidence = (validation.evidence_source_path, validation.alignment_offset_microseconds)
    if validation.alignment_verified and None in verified_evidence:
        raise ValueError("verified chronology requires a persisted source and alignment offset")


def _validate_evidence_path(validation: ChronologyValidation) -> None:
    if validation.evidence_source_path is not None and validation.evidence_source_path.is_absolute():
        raise ValueError("chronology evidence paths must be relative")


def _validate_chronology_counts(validation: ChronologyValidation) -> None:
    if (
        min(
            validation.total_rows,
            validation.parseable_rows,
            validation.invalid_rows,
            validation.duplicate_timestamp_count,
        )
        < 0
    ):
        raise ValueError("chronology counts must be non-negative")
    if validation.parseable_rows + validation.invalid_rows != validation.total_rows:
        raise ValueError("parseable and invalid chronology rows must total all rows")
