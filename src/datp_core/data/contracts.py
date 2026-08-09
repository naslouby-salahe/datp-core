"""Immutable records for audited dataset ingestion and publication, and their canonical serialization."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pyarrow as pa

import datp_core.core.identifiers as domain_enums
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.json import canonical_json_text, canonical_mapping
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    AvailabilityStatus,
    CanonicalizationContractName,
    ChronologyGroupIdentity,
    ColumnName,
    DatasetId,
    NonEmptyString,
    PhysicalSchemaText,
    SourceIdentity,
    ValidationSourceContext,
)
from datp_core.core.numeric import (
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
        if type(self.dataset) is not DatasetId:
            raise TypeError("raw sources require a typed dataset")
        if type(self.size_bytes) is not ByteCount:
            raise TypeError("raw sources require a typed byte count")
        if type(self.checksum) is not Checksum:
            raise TypeError("raw sources require a typed checksum")
        if type(self.role) is not SourceFileRole:
            raise TypeError("raw sources require a typed role")
        if self.observed_row_count is not None and type(self.observed_row_count) is not RowCount:
            raise TypeError("raw sources require a typed observed row count")
        if self.relative_path.is_absolute():
            raise ValueError("raw source paths must be relative")


@dataclass(frozen=True, slots=True)
class ExcludedSourceFile:
    dataset: DatasetId
    relative_path: Path
    reason: ExclusionReason

    def __post_init__(self) -> None:
        if type(self.dataset) is not DatasetId:
            raise TypeError("excluded sources require a typed dataset")
        if type(self.reason) is not ExclusionReason:
            raise TypeError("excluded sources require a typed exclusion reason")
        if self.relative_path.is_absolute():
            raise ValueError("excluded source paths must be relative")


@dataclass(frozen=True, slots=True)
class RawDatasetInventory:
    dataset: DatasetId
    sources: tuple[RawSourceFile, ...]
    accepted_source_count: SourceFileCount
    excluded_source_count: SourceFileCount
    excluded_sources: tuple[ExcludedSourceFile, ...]
    accepted_row_count: RowCount | None
    checksum: Checksum

    def __post_init__(self) -> None:
        _validate_inventory_sources(self.sources, self.accepted_source_count)
        _validate_inventory_count(self.excluded_source_count)
        _validate_excluded_sources(self.excluded_sources, self.excluded_source_count)


@dataclass(frozen=True, slots=True)
class CanonicalColumn:
    name: ColumnName
    source_name: ColumnName
    dtype: ColumnLogicalType
    role: CanonicalColumnRole
    nullable: bool
    position: CanonicalColumnPosition

    def __post_init__(self) -> None:
        if type(self.dtype) is not ColumnLogicalType:
            raise TypeError("canonical columns require a ColumnLogicalType dtype")
        if type(self.role) is not CanonicalColumnRole:
            raise TypeError("canonical columns require a typed role")
        if type(self.nullable) is not bool:
            raise TypeError("canonical column nullability must be boolean")
        if type(self.position) is not CanonicalColumnPosition:
            raise TypeError("canonical columns require a typed position")


@dataclass(frozen=True, slots=True)
class CanonicalSchema:
    dataset: DatasetId
    columns: tuple[CanonicalColumn, ...]
    feature_columns: tuple[ColumnName, ...]
    label_columns: tuple[ColumnName, ...]
    provenance_columns: tuple[ColumnName, ...]
    physical_schema: PhysicalSchemaText
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
        if type(self.zero_based_row_index) is not SourceRowIndex:
            raise TypeError("source row references require a typed zero-based index")


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
        if type(self.affected_count) is not RowCount or not self.evidence or self.affected_count.value < 1:
            raise ValueError("exclusions require evidence and a positive affected count")


@dataclass(frozen=True, slots=True)
class DatasetValidationIssue:
    severity: ValidationSeverity
    code: DatasetValidationCode
    dataset: DatasetId
    source_context: ValidationSourceContext
    reason: NonEmptyString
    affected_count: RowCount

    def __post_init__(self) -> None:
        if type(self.code) is not DatasetValidationCode:
            raise ValueError("validation issues require a DatasetValidationCode")
        if type(self.affected_count) is not RowCount or not self.reason or self.affected_count.value < 1:
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
        if not all(type(value) is RowCount for value in (self.accepted_rows, self.excluded_rows, self.invalid_rows)):
            raise TypeError("validation reports require typed row counts")
        if type(self.status) is not AvailabilityStatus:
            raise TypeError("validation reports require a typed availability status")
        if type(self.warning_count) is not ValidationIssueCount:
            raise TypeError("validation reports require a typed warning count")
        if self.warning_count.value != _warning_count(self.issues):
            raise ValueError("warning count must match warning issues")
        if self.excluded_rows != _excluded_row_count(self.exclusions):
            raise ValueError("excluded rows must match recorded exclusions")


@dataclass(frozen=True, slots=True)
class ModelInputEligibilityPolicy[EligibilityReasonT: StrEnum]:
    dataset: DatasetId
    label_column: ColumnName
    feature_columns: tuple[ColumnName, ...]
    exclusion_reasons: tuple[EligibilityReasonT, ...]

    def __post_init__(self) -> None:
        if not self.feature_columns:
            raise ValueError("model-input eligibility policies require feature columns")
        if len(self.feature_columns) != len(frozenset(self.feature_columns)):
            raise ValueError("model-input eligibility feature columns must be unique")
        if len(self.exclusion_reasons) != len(frozenset(self.exclusion_reasons)):
            raise ValueError("model-input eligibility reasons must be unique")


def _validate_canonical_columns(columns: tuple[CanonicalColumn, ...], physical_schema: PhysicalSchemaText) -> None:
    _require_schema_content(columns, physical_schema)
    _validate_column_order_and_names(columns)


def _require_schema_content(columns: tuple[CanonicalColumn, ...], physical_schema: PhysicalSchemaText) -> None:
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
    declared: tuple[ColumnName, ...],
    role: CanonicalColumnRole,
    subject: str,
) -> None:
    names = tuple(column.name for column in columns if column.role is role)
    if names != declared:
        raise ValueError(f"{subject} columns must match ordered canonical {subject} declarations")


def _validate_inventory_sources(sources: tuple[RawSourceFile, ...], accepted_source_count: SourceFileCount) -> None:
    if type(sources) is not tuple:
        raise TypeError("sources must be an immutable tuple")
    if type(accepted_source_count) is not SourceFileCount:
        raise TypeError("raw inventories require a typed accepted source count")
    if accepted_source_count.value != len(sources):
        raise ValueError("accepted source count must equal source tuple length")
    relative_paths = tuple(source.relative_path for source in sources)
    if len(relative_paths) != len(frozenset(relative_paths)):
        raise ValueError("raw inventory source paths must be unique")


def _validate_inventory_count(excluded_source_count: SourceFileCount) -> None:
    if type(excluded_source_count) is not SourceFileCount:
        raise TypeError("raw inventories require a typed excluded source count")


def _validate_excluded_sources(
    excluded_sources: tuple[ExcludedSourceFile, ...],
    excluded_source_count: SourceFileCount,
) -> None:
    if type(excluded_sources) is not tuple:
        raise TypeError("excluded sources must be an immutable tuple")
    if len(excluded_sources) != excluded_source_count.value:
        raise ValueError("excluded source count must equal excluded source tuple length")
    relative_paths = tuple(source.relative_path for source in excluded_sources)
    if len(relative_paths) != len(frozenset(relative_paths)):
        raise ValueError("excluded source paths must be unique")


def _validate_report_collections(
    issues: tuple[DatasetValidationIssue, ...], exclusions: tuple[DatasetExclusion, ...]
) -> None:
    if type(issues) is not tuple:
        raise TypeError("validation issues must be an immutable tuple")
    if type(exclusions) is not tuple:
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
    source_identity: SourceIdentity | None = None

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
        if type(self.assets) is not tuple or not self.assets:
            raise ValueError("materialized datasets require immutable canonical assets")


@dataclass(frozen=True, slots=True)
class ChronologyValidation:
    group_identity: ChronologyGroupIdentity
    status: AvailabilityStatus
    total_rows: RowCount
    parseable_rows: RowCount
    invalid_rows: RowCount
    duplicate_timestamp_count: RowCount
    is_monotonic: bool
    reason: NonEmptyString
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
    if not validation.reason:
        raise ValueError("chronology validations require a reason")


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
    if not all(type(value) is RowCount for value in required_counts):
        raise TypeError("chronology validation requires typed row counts")
    if validation.evidence_row_count is not None and type(validation.evidence_row_count) is not RowCount:
        raise TypeError("chronology evidence requires a typed row count")
    if validation.parseable_rows.value + validation.invalid_rows.value != validation.total_rows.value:
        raise ValueError("parseable and invalid chronology rows must total all rows")


class SchemaChecksumDocument(StrictModel):
    canonicalization_contract: CanonicalizationContractName
    columns: tuple[CanonicalColumn, ...]
    dataset: DatasetId
    physical_schema: PhysicalSchemaText


class ManifestAssetEntry(StrictModel):
    checksum: Checksum
    columns: tuple[ColumnName, ...]
    path: str
    row_count: RowCount
    role: str
    source_identity: SourceIdentity | None = None


class ManifestChronologyEntry(StrictModel):
    group_identity: ChronologyGroupIdentity
    status: AvailabilityStatus
    total_rows: RowCount
    parseable_rows: RowCount
    invalid_rows: RowCount
    duplicate_timestamp_count: RowCount
    is_monotonic: bool
    reason: NonEmptyString
    temporal_eligible: bool
    evidence_source_path: str | None = None
    evidence_row_count: RowCount | None = None
    alignment_verified: bool = False
    alignment_offset_microseconds: int | None = None
    skipped_evidence_rows: RowCount = RowCount(0)
    trailing_evidence_rows: RowCount = RowCount(0)


class ManifestRawSourceEntry(StrictModel):
    dataset: DatasetId
    relative_path: str
    size_bytes: ByteCount
    checksum: Checksum
    role: SourceFileRole
    observed_row_count: RowCount | None = None


class ManifestExcludedSourceEntry(StrictModel):
    dataset: DatasetId
    relative_path: str
    reason: ExclusionReason


class ManifestInventoryEntry(StrictModel):
    dataset: DatasetId
    sources: tuple[ManifestRawSourceEntry, ...]
    accepted_source_count: SourceFileCount
    excluded_source_count: SourceFileCount
    excluded_sources: tuple[ManifestExcludedSourceEntry, ...]
    accepted_row_count: RowCount | None = None
    checksum: Checksum


class ManifestSourceRowEntry(StrictModel):
    source: ManifestRawSourceEntry
    zero_based_row_index: SourceRowIndex


class ManifestExclusionEntry(StrictModel):
    dataset: DatasetId
    source_path: str | None = None
    source_row: ManifestSourceRowEntry | None = None
    reason: ExclusionReason
    evidence: str
    affected_count: RowCount


class ManifestValidationIssueEntry(StrictModel):
    severity: ValidationSeverity
    code: DatasetValidationCode
    dataset: DatasetId
    source_context: ValidationSourceContext
    reason: NonEmptyString
    affected_count: RowCount


class ManifestValidationReportEntry(StrictModel):
    dataset: DatasetId
    issues: tuple[ManifestValidationIssueEntry, ...]
    exclusions: tuple[ManifestExclusionEntry, ...]
    accepted_rows: RowCount
    excluded_rows: RowCount
    invalid_rows: RowCount
    warning_count: ValidationIssueCount
    status: AvailabilityStatus


class ManifestEligibilityPolicyEntry(StrictModel):
    dataset: DatasetId
    label_column: ColumnName
    feature_columns: tuple[ColumnName, ...]
    exclusion_reasons: tuple[str, ...]


class CanonicalManifestDocument(StrictModel):
    assets: tuple[ManifestAssetEntry, ...]
    canonicalization_contract: CanonicalizationContractName
    chronology: tuple[ManifestChronologyEntry, ...]
    dataset: DatasetId
    eligibility_policy: ManifestEligibilityPolicyEntry | None = None
    inventory: ManifestInventoryEntry
    schema_checksum: Checksum
    validation_report: ManifestValidationReportEntry


_CANONICAL_PUBLICATION_CONTRACT = CanonicalizationContractName("canonical_publication_contract")
_COMPLETE_NAME = CanonicalPublicationArtifact.COMPLETE
_MANIFEST_NAME = CanonicalPublicationArtifact.MANIFEST
_SCHEMA_NAME = CanonicalPublicationArtifact.SCHEMA
_SOURCE_STATE_NAME = CanonicalPublicationArtifact.SOURCE_STATE


def complete_digest(manifest_payload: str, schema_payload: str) -> Checksum:
    return Checksum.from_text(f"{manifest_payload}\n{schema_payload}")


def schema_content(schema: CanonicalSchema) -> str:
    return canonical_json_text(schema)


def schema_checksum_document_json(
    dataset: DatasetId, columns: tuple[CanonicalColumn, ...], physical_schema: pa.Schema
) -> str:
    return canonical_json_text(
        SchemaChecksumDocument(
            canonicalization_contract=_CANONICAL_PUBLICATION_CONTRACT,
            columns=columns,
            dataset=dataset,
            physical_schema=PhysicalSchemaText(
                physical_schema.to_string(show_field_metadata=True, show_schema_metadata=True)
            ),
        )
    )


def publication_artifact_names() -> tuple[
    CanonicalPublicationArtifact,
    CanonicalPublicationArtifact,
    CanonicalPublicationArtifact,
    CanonicalPublicationArtifact,
]:
    return _COMPLETE_NAME, _MANIFEST_NAME, _SCHEMA_NAME, _SOURCE_STATE_NAME


@dataclass(frozen=True, slots=True)
class ManifestSerializationRequest[EligibilityReasonT: StrEnum]:
    dataset: DatasetId
    canonicalization_contract: CanonicalizationContractName
    schema_checksum: Checksum
    inventory: RawDatasetInventory
    validation_report: DatasetValidationReport
    chronology: tuple[ChronologyValidation, ...] = ()
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None


def manifest_chronology_entry(value: ChronologyValidation) -> ManifestChronologyEntry:
    return ManifestChronologyEntry.model_validate(canonical_mapping(value))


def manifest_eligibility_entry[EligibilityReasonT: StrEnum](
    value: ModelInputEligibilityPolicy[EligibilityReasonT] | None,
) -> ManifestEligibilityPolicyEntry | None:
    return None if value is None else ManifestEligibilityPolicyEntry.model_validate(canonical_mapping(value))


def manifest_inventory_entry(value: RawDatasetInventory) -> ManifestInventoryEntry:
    return ManifestInventoryEntry.model_validate(canonical_mapping(value))


def manifest_validation_report_entry(value: DatasetValidationReport) -> ManifestValidationReportEntry:
    return ManifestValidationReportEntry.model_validate(canonical_mapping(value))


class SourceStateEntryDocument(StrictModel):
    modified_time_nanoseconds: int
    path: str
    size_bytes: ByteCount


class SourceStateDocument(StrictModel):
    content_checksum_verified: bool = False
    dataset: DatasetId
    manifest_checksum: Checksum
    sources: tuple[SourceStateEntryDocument, ...]
