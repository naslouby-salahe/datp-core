"""Immutable records for audited dataset ingestion and publication."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import datp_core.domain.enums as domain_enums
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import AvailabilityStatus, DatasetId
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import (
    ByteCount,
    CanonicalColumnPosition,
    RowCount,
    SourceFileCount,
    SourceRowIndex,
    ValidationIssueCount,
)


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


class CanonicalAssetRole(StrEnum):
    CANONICAL_DATA = "canonical_data"


@dataclass(frozen=True, slots=True)
class RawSourceFile:
    dataset: DatasetId
    relative_path: Path
    size_bytes: ByteCount
    checksum: Checksum
    role: SourceFileRole
    observed_row_count: RowCount | None

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, DatasetId):
            raise TypeError("raw sources require a typed dataset")
        if not isinstance(self.size_bytes, ByteCount):
            raise TypeError("raw sources require a typed byte count")
        if not isinstance(self.checksum, Checksum):
            raise TypeError("raw sources require a typed checksum")
        if not isinstance(self.role, SourceFileRole):
            raise TypeError("raw sources require a typed role")
        if self.observed_row_count is not None and not isinstance(self.observed_row_count, RowCount):
            raise TypeError("raw sources require a typed observed row count")
        if self.relative_path.is_absolute():
            raise ValueError("raw source paths must be relative")


@dataclass(frozen=True, slots=True)
class RawDatasetInventory:
    dataset: DatasetId
    sources: tuple[RawSourceFile, ...]
    accepted_source_count: SourceFileCount
    excluded_source_count: SourceFileCount
    accepted_row_count: RowCount | None
    checksum: Checksum

    def __post_init__(self) -> None:
        _validate_inventory_sources(self.sources, self.accepted_source_count)
        _validate_inventory_count(self.excluded_source_count)


@dataclass(frozen=True, slots=True)
class CanonicalColumn:
    name: str
    source_name: str
    dtype: ColumnLogicalType
    role: CanonicalColumnRole
    nullable: bool
    position: CanonicalColumnPosition

    def __post_init__(self) -> None:
        if not self.name or not self.source_name:
            raise ValueError("canonical columns require non-empty names")
        if not isinstance(self.dtype, ColumnLogicalType):
            raise TypeError("canonical columns require a ColumnLogicalType dtype")
        if not isinstance(self.role, CanonicalColumnRole):
            raise TypeError("canonical columns require a typed role")
        if not isinstance(self.nullable, bool):
            raise TypeError("canonical column nullability must be boolean")
        if not isinstance(self.position, CanonicalColumnPosition):
            raise TypeError("canonical columns require a typed position")


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
    zero_based_row_index: SourceRowIndex

    def __post_init__(self) -> None:
        if not isinstance(self.zero_based_row_index, SourceRowIndex):
            raise TypeError("source row references require a typed zero-based index")


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
    affected_count: RowCount

    def __post_init__(self) -> None:
        if self.source_path is None and self.source_row is None:
            raise ValueError("an exclusion requires source context")
        if not isinstance(self.affected_count, RowCount) or not self.evidence or self.affected_count.value < 1:
            raise ValueError("exclusions require evidence and a positive affected count")


@dataclass(frozen=True, slots=True)
class DatasetValidationIssue:
    severity: ValidationSeverity
    code: DatasetValidationCode
    dataset: DatasetId
    source_context: str
    reason: str
    affected_count: RowCount

    def __post_init__(self) -> None:
        if not isinstance(self.code, DatasetValidationCode):
            raise ValueError("validation issues require a DatasetValidationCode")
        if (
            not isinstance(self.affected_count, RowCount)
            or not self.source_context
            or not self.reason
            or self.affected_count.value < 1
        ):
            raise ValueError("validation issues require complete source evidence")


@dataclass(frozen=True, slots=True)
class DatasetValidationReport:
    dataset: DatasetId
    issues: tuple[DatasetValidationIssue, ...]
    exclusions: tuple[DatasetExclusion, ...]
    accepted_rows: RowCount
    excluded_rows: RowCount
    invalid_rows: RowCount
    warning_count: ValidationIssueCount
    status: AvailabilityStatus

    def __post_init__(self) -> None:
        _validate_report_collections(self.issues, self.exclusions)
        if not all(
            isinstance(value, RowCount) for value in (self.accepted_rows, self.excluded_rows, self.invalid_rows)
        ):
            raise TypeError("validation reports require typed row counts")
        if not isinstance(self.status, AvailabilityStatus):
            raise TypeError("validation reports require a typed availability status")
        if not isinstance(self.warning_count, ValidationIssueCount):
            raise TypeError("validation reports require a typed warning count")
        if self.warning_count.value != _warning_count(self.issues):
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
    if tuple(column.position.value for column in columns) != tuple(range(len(columns))):
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


def _validate_inventory_sources(sources: tuple[RawSourceFile, ...], accepted_source_count: SourceFileCount) -> None:
    if not isinstance(sources, tuple):
        raise TypeError("sources must be an immutable tuple")
    if not isinstance(accepted_source_count, SourceFileCount):
        raise TypeError("raw inventories require a typed accepted source count")
    if accepted_source_count.value != len(sources):
        raise ValueError("accepted source count must equal source tuple length")
    relative_paths = tuple(source.relative_path for source in sources)
    if len(relative_paths) != len(frozenset(relative_paths)):
        raise ValueError("raw inventory source paths must be unique")


def _validate_inventory_count(excluded_source_count: SourceFileCount) -> None:
    if not isinstance(excluded_source_count, SourceFileCount):
        raise TypeError("raw inventories require a typed excluded source count")


def _validate_report_collections(
    issues: tuple[DatasetValidationIssue, ...], exclusions: tuple[DatasetExclusion, ...]
) -> None:
    if not isinstance(issues, tuple):
        raise TypeError("validation issues must be an immutable tuple")
    if not isinstance(exclusions, tuple):
        raise TypeError("dataset exclusions must be an immutable tuple")


def _warning_count(issues: tuple[DatasetValidationIssue, ...]) -> int:
    return sum(issue.severity is ValidationSeverity.WARNING for issue in issues)


def _excluded_row_count(exclusions: tuple[DatasetExclusion, ...]) -> RowCount:
    return RowCount(sum(exclusion.affected_count.value for exclusion in exclusions))


@dataclass(frozen=True, slots=True)
class MaterializedCanonicalAsset[AssetRoleT: StrEnum]:
    path: Path
    role: AssetRoleT
    row_count: RowCount
    source_identity: str | None = None

    def __post_init__(self) -> None:
        if not self.path.is_absolute():
            raise ValueError("materialized canonical assets require an absolute path")


@dataclass(frozen=True, slots=True)
class MaterializedDataset[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum]:
    dataset: DatasetId
    canonical_root: Path
    assets: tuple[MaterializedCanonicalAsset[AssetRoleT], ...]
    manifest_path: Path
    schema: CanonicalSchema
    row_count: RowCount
    source_inventory_checksum: Checksum
    publication_status: domain_enums.PublicationStatus
    inventory: RawDatasetInventory
    validation_report: DatasetValidationReport
    chronology: tuple["ChronologyValidation", ...] = ()
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.assets, tuple) or not self.assets:
            raise ValueError("materialized datasets require immutable canonical assets")


@dataclass(frozen=True, slots=True)
class ChronologyValidation:
    group_identity: str
    status: AvailabilityStatus
    total_rows: RowCount
    parseable_rows: RowCount
    invalid_rows: RowCount
    duplicate_timestamp_count: RowCount
    is_monotonic: bool
    reason: str
    temporal_eligible: bool
    evidence_source_path: Path | None = None
    evidence_row_count: RowCount | None = None
    alignment_verified: bool = False
    alignment_offset_microseconds: int | None = None
    skipped_evidence_rows: RowCount = RowCount(0)
    trailing_evidence_rows: RowCount = RowCount(0)

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
    _validate_optional_non_negative(validation.alignment_offset_microseconds, "chronology alignment offsets")


def _validate_optional_non_negative(value: int | None, subject: str) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{subject} must be non-negative")


def _validate_verified_evidence(validation: ChronologyValidation) -> None:
    verified_evidence = (validation.evidence_source_path, validation.alignment_offset_microseconds)
    if validation.alignment_verified and None in verified_evidence:
        raise ValueError("verified chronology requires a persisted source and alignment offset")


def _validate_evidence_path(validation: ChronologyValidation) -> None:
    if validation.evidence_source_path is not None and validation.evidence_source_path.is_absolute():
        raise ValueError("chronology evidence paths must be relative")


def _validate_chronology_counts(validation: ChronologyValidation) -> None:
    required_counts = (
        validation.total_rows,
        validation.parseable_rows,
        validation.invalid_rows,
        validation.duplicate_timestamp_count,
        validation.skipped_evidence_rows,
        validation.trailing_evidence_rows,
    )
    if not all(isinstance(value, RowCount) for value in required_counts):
        raise TypeError("chronology validation requires typed row counts")
    if validation.evidence_row_count is not None and not isinstance(validation.evidence_row_count, RowCount):
        raise TypeError("chronology evidence requires a typed row count")
    if validation.parseable_rows.value + validation.invalid_rows.value != validation.total_rows.value:
        raise ValueError("parseable and invalid chronology rows must total all rows")


class SchemaChecksumDocument(StrictModel):
    canonicalization_contract: str
    columns: tuple[CanonicalColumn, ...]
    dataset: DatasetId
    physical_schema: str


class _AssetEntry(StrictModel):
    checksum: str
    columns: tuple[str, ...]
    path: str
    row_count: RowCount
    role: str
    source_identity: str | None = None


class _ChronologyEntry(StrictModel):
    group_identity: str
    status: str
    total_rows: RowCount
    parseable_rows: RowCount
    invalid_rows: RowCount
    duplicate_timestamp_count: RowCount
    is_monotonic: bool
    reason: str
    temporal_eligible: bool
    evidence_source_path: str | None = None
    evidence_row_count: RowCount | None = None
    alignment_verified: bool = False
    alignment_offset_microseconds: int | None = None
    skipped_evidence_rows: RowCount = RowCount(0)
    trailing_evidence_rows: RowCount = RowCount(0)


class _RawSourceEntry(StrictModel):
    dataset: str = ""
    relative_path: str
    size_bytes: ByteCount
    checksum: str
    role: str
    observed_row_count: RowCount | None = None


class _InventoryEntry(StrictModel):
    dataset: str = ""
    sources: tuple[_RawSourceEntry, ...]
    accepted_source_count: SourceFileCount
    excluded_source_count: SourceFileCount
    accepted_row_count: RowCount | None = None
    checksum: str


class _SourceRowEntry(StrictModel):
    source: _RawSourceEntry
    zero_based_row_index: SourceRowIndex


class _ExclusionEntry(StrictModel):
    dataset: str = ""
    source_path: str | None = None
    source_row: _SourceRowEntry | None = None
    reason: str
    evidence: str
    affected_count: RowCount


class _ValidationIssueEntry(StrictModel):
    severity: str
    code: str
    dataset: str = ""
    source_context: str
    reason: str
    affected_count: RowCount


class _ValidationReportEntry(StrictModel):
    dataset: str = ""
    issues: tuple[_ValidationIssueEntry, ...]
    exclusions: tuple[_ExclusionEntry, ...]
    accepted_rows: RowCount
    excluded_rows: RowCount
    invalid_rows: RowCount
    warning_count: ValidationIssueCount
    status: str


class _EligibilityPolicyEntry(StrictModel):
    dataset: str = ""
    label_column: str
    feature_columns: tuple[str, ...]
    exclusion_reasons: tuple[str, ...]


class CanonicalManifestDocument(StrictModel):
    assets: tuple[_AssetEntry, ...]
    canonicalization_contract: str
    chronology: tuple[_ChronologyEntry, ...]
    dataset: DatasetId
    eligibility_policy: _EligibilityPolicyEntry | None = None
    inventory: _InventoryEntry
    schema_checksum: str
    validation_report: _ValidationReportEntry


class SourceStateEntryDocument(StrictModel):
    modified_time_nanoseconds: int
    path: str
    size_bytes: ByteCount


class SourceStateDocument(StrictModel):
    content_checksum_verified: bool = False
    dataset: DatasetId
    manifest_checksum: str
    sources: tuple[SourceStateEntryDocument, ...]
