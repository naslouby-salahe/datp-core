"""Canonical publication reuse, source-state comparison, and manifest serialization."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from filelock import FileLock
from pydantic import BaseModel, ConfigDict, Field

from datp_core.datasets.models import (
    CanonicalAssetRole,
    CanonicalColumn,
    CanonicalPublicationArtifact,
    CanonicalSchema,
    ChronologyValidation,
    DatasetExclusion,
    DatasetValidationCode,
    DatasetValidationIssue,
    DatasetValidationReport,
    ExclusionReason,
    MaterializedCanonicalAsset,
    MaterializedDataset,
    ModelInputEligibilityPolicy,
    PublicationStatus,
    RawDatasetInventory,
    RawSourceFile,
    SourceFileRole,
    SourceRowReference,
    ValidationSeverity,
)
from datp_core.domain.enums import AvailabilityStatus, DatasetId
from datp_core.domain.values import ByteCount, Checksum
from datp_core.protocols.models import DATA_ROOT

_CANONICAL_PUBLICATION_CONTRACT = "canonical_publication_contract"
_COMPLETE_NAME = CanonicalPublicationArtifact.COMPLETE
_MANIFEST_NAME = CanonicalPublicationArtifact.MANIFEST
_SCHEMA_NAME = CanonicalPublicationArtifact.SCHEMA
_SOURCE_STATE_NAME = CanonicalPublicationArtifact.SOURCE_STATE

SourcePathResolver = Callable[[Path], Path]


class _SerializedColumn(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dtype: str
    name: str
    nullable: bool
    position: int
    role: str
    source_name: str


class _SerializedSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    columns: tuple[_SerializedColumn, ...]
    dataset: str
    feature_columns: tuple[str, ...]
    label_columns: tuple[str, ...]
    physical_schema: str
    provenance_columns: tuple[str, ...]
    schema_checksum: str


class _SchemaChecksumDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    canonicalization_contract: str
    columns: tuple[_SerializedColumn, ...]
    dataset: str
    physical_schema: str


class _SerializedSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checksum: str
    path: str
    role: str
    row_count: int | None
    size_bytes: int


class _SerializedInventory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted_row_count: int | None
    accepted_source_count: int
    checksum: str
    excluded_source_count: int
    sources: tuple[_SerializedSource, ...]


class _SerializedIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    affected_count: int
    code: str
    reason: str
    severity: str
    source_context: str


class _SerializedExclusion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    affected_count: int
    evidence: str
    reason: str
    source_path: str | None
    source_row_index: int | None


class _SerializedValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted_rows: int
    excluded_rows: int
    exclusions: tuple[_SerializedExclusion, ...]
    invalid_rows: int
    issues: tuple[_SerializedIssue, ...]
    status: str
    warning_count: int


class _SerializedAsset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checksum: str
    columns: tuple[str, ...]
    path: str
    row_count: int
    role: str
    source_identity: str | None = None


class _SerializedChronology(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    alignment_offset_microseconds: int | None
    alignment_verified: bool
    duplicate_timestamp_count: int
    evidence_row_count: int | None
    evidence_source_path: str | None
    group_identity: str
    invalid_rows: int
    is_monotonic: bool
    parseable_rows: int
    reason: str
    skipped_evidence_rows: int
    status: str
    temporal_eligible: bool
    total_rows: int
    trailing_evidence_rows: int


class _SerializedEligibilityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checksum: str
    feature_columns: tuple[str, ...]
    label_column: str
    reasons: tuple[str, ...]


class _SerializedManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    assets: tuple[_SerializedAsset, ...]
    canonicalization_contract: str
    chronology: tuple[_SerializedChronology, ...]
    dataset: str
    eligibility_policy: _SerializedEligibilityPolicy | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    inventory: _SerializedInventory
    schema_checksum: str
    validation_report: _SerializedValidationReport


class _SerializedSourceStateEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    modified_time_nanoseconds: int
    path: str
    size_bytes: int


class _SerializedSourceState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_checksum_verified: bool = False
    dataset: str
    manifest_checksum: str
    sources: tuple[_SerializedSourceStateEntry, ...]


@dataclass(frozen=True, slots=True)
class CanonicalAssetLayout[AssetRoleT: StrEnum]:
    relative_path: Path
    role: AssetRoleT
    source_identity: str | None = None

    def __post_init__(self) -> None:
        if not _is_canonical_relative_path(self.relative_path):
            raise ValueError("canonical asset layouts must use data-root-relative paths")


@dataclass(frozen=True, slots=True)
class CanonicalAsset[AssetRoleT: StrEnum]:
    relative_path: Path
    checksum: Checksum
    row_count: int
    columns: tuple[str, ...]
    role: AssetRoleT
    source_identity: str | None = None

    def __post_init__(self) -> None:
        if not _is_canonical_relative_path(self.relative_path):
            raise ValueError("canonical assets require a relative path, columns, and a non-negative row count")
        if not self.columns:
            raise ValueError("canonical assets require a relative path, columns, and a non-negative row count")
        if self.row_count < 0:
            raise ValueError("canonical assets require a relative path, columns, and a non-negative row count")


def canonical_asset_path(root: Path, relative_path: Path) -> Path:
    if not _is_canonical_relative_path(relative_path):
        raise ValueError("canonical assets must remain below the data branch")
    candidate = root / relative_path
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError("canonical asset path escapes its publication root")
    return candidate


def _is_canonical_relative_path(path: Path) -> bool:
    return not path.is_absolute() and path.parts[:1] == (DATA_ROOT.name,) and ".." not in path.parts


def canonical_directory(canonical_root: Path, schema: CanonicalSchema) -> Path:
    return canonical_root / schema.dataset.value


def schema_content(schema: CanonicalSchema) -> str:
    return _SerializedSchema(
        columns=tuple(_serialized_column(column) for column in schema.columns),
        dataset=schema.dataset.value,
        feature_columns=schema.feature_columns,
        label_columns=schema.label_columns,
        physical_schema=schema.physical_schema,
        provenance_columns=schema.provenance_columns,
        schema_checksum=schema.checksum.value,
    ).model_dump_json()


def schema_checksum_document_json(
    dataset: DatasetId, columns: tuple[CanonicalColumn, ...], physical_schema: pa.Schema
) -> str:
    return _SchemaChecksumDocument(
        canonicalization_contract=_CANONICAL_PUBLICATION_CONTRACT,
        columns=tuple(_serialized_column(column) for column in columns),
        dataset=dataset.value,
        physical_schema=physical_schema.to_string(show_field_metadata=True, show_schema_metadata=True),
    ).model_dump_json()


def file_checksum(path: Path) -> Checksum:
    digest = sha256()
    with path.open("rb") as source:
        while chunk := source.read(1_048_576):
            digest.update(chunk)
    return Checksum(digest.hexdigest())


def complete_content(manifest: str, schema: str) -> str:
    return Checksum(sha256(f"{manifest}\n{schema}".encode()).hexdigest()).value


def canonical_publication_contract() -> str:
    return _CANONICAL_PUBLICATION_CONTRACT


def publication_artifact_names() -> tuple[str, str, str, str]:
    return _COMPLETE_NAME, _MANIFEST_NAME, _SCHEMA_NAME, _SOURCE_STATE_NAME


@dataclass(frozen=True, slots=True)
class CanonicalReuseRequest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum]:
    canonical_root: Path
    schema: CanonicalSchema
    canonicalization_contract: str
    source_paths: tuple[Path, ...]
    source_path_resolver: SourcePathResolver
    asset_role_type: type[AssetRoleT]
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None


@dataclass(frozen=True, slots=True)
class PublicationMatchRequest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum]:
    """Structural fields required to validate a completed canonical publication for reuse."""

    schema: CanonicalSchema
    canonicalization_contract: str
    inventory: RawDatasetInventory
    validation_report: DatasetValidationReport
    expected_assets: tuple[CanonicalAssetLayout[AssetRoleT], ...]
    chronology: tuple[ChronologyValidation, ...]
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None


@dataclass(frozen=True, slots=True)
class SourceStateProbe:
    target: Path
    dataset: DatasetId
    source_paths: tuple[Path, ...]
    manifest: str
    source_path_resolver: SourcePathResolver


@dataclass(frozen=True, slots=True)
class PublicationFiles:
    target: Path
    schema_file: Path
    manifest_file: Path
    complete_file: Path


def completed_publication_is_reusable[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    target: Path, publication: PublicationMatchRequest[AssetRoleT, EligibilityReasonT]
) -> bool:
    files = PublicationFiles(
        target,
        target / _SCHEMA_NAME,
        target / _MANIFEST_NAME,
        target / _COMPLETE_NAME,
    )
    manifest = _reusable_manifest(files, publication)
    if manifest is None:
        return False
    if tuple((Path(asset.path), asset.role, asset.source_identity) for asset in manifest.assets) != tuple(
        (layout.relative_path, layout.role.value, layout.source_identity) for layout in publication.expected_assets
    ):
        return False
    return all(asset_is_valid(target, asset, publication.schema.physical_schema) for asset in manifest.assets)


def reuse_published_canonical[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    request: CanonicalReuseRequest[AssetRoleT, EligibilityReasonT],
) -> MaterializedDataset[AssetRoleT, EligibilityReasonT] | None:
    """Return a complete, source-current canonical publication without reading raw rows."""
    if not request.source_paths:
        return None
    target = canonical_directory(request.canonical_root, request.schema)
    with FileLock(f"{target}.lock"):
        reusable = _fast_reusable_manifest(target, request)
        if reusable is None:
            return None
        manifest, _ = reusable
        return _reused_materialized_dataset(request, target, manifest)


def _fast_reusable_manifest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    target: Path, request: CanonicalReuseRequest[AssetRoleT, EligibilityReasonT]
) -> tuple[_SerializedManifest, str] | None:
    schema = request.schema
    schema_file = target / _SCHEMA_NAME
    manifest_file = target / _MANIFEST_NAME
    complete_file = target / _COMPLETE_NAME
    published_manifest = _read_manifest(target, schema_file, manifest_file, complete_file)
    if published_manifest is None:
        return None
    manifest, serialized_manifest = published_manifest
    compatible = (
        _documents_match_publication(schema_file, complete_file, serialized_manifest, schema),
        manifest.dataset == schema.dataset.value,
        manifest.schema_checksum == schema.checksum.value,
        manifest.canonicalization_contract == request.canonicalization_contract,
        manifest.eligibility_policy == _serialized_eligibility_policy(request.eligibility_policy),
        _assets_have_declared_metadata(target, manifest.assets, schema.physical_schema),
        _source_state_matches(
            SourceStateProbe(
                target,
                schema.dataset,
                request.source_paths,
                serialized_manifest,
                request.source_path_resolver,
            )
        ),
    )
    return (manifest, serialized_manifest) if all(compatible) else None


def _reused_materialized_dataset[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    request: CanonicalReuseRequest[AssetRoleT, EligibilityReasonT],
    target: Path,
    manifest: _SerializedManifest,
) -> MaterializedDataset[AssetRoleT, EligibilityReasonT]:
    schema = request.schema
    inventory = _reused_inventory(schema.dataset, manifest.inventory)
    report = _reused_validation_report(schema.dataset, manifest.validation_report, inventory)
    assets = tuple(
        MaterializedCanonicalAsset(
            canonical_asset_path(target, Path(asset.path)).resolve(),
            request.asset_role_type(asset.role),
            asset.row_count,
            asset.source_identity,
        )
        for asset in manifest.assets
    )
    return MaterializedDataset(
        dataset=schema.dataset,
        canonical_root=target,
        assets=assets,
        manifest_path=target / _MANIFEST_NAME,
        schema=schema,
        row_count=(
            inventory.accepted_row_count
            if inventory.accepted_row_count is not None
            else sum(asset.row_count for asset in assets if asset.role is CanonicalAssetRole.CANONICAL_DATA)
        ),
        source_inventory_checksum=inventory.checksum,
        publication_status=PublicationStatus.REUSED,
        inventory=inventory,
        validation_report=report,
        chronology=tuple(_reused_chronology(validation) for validation in manifest.chronology),
        eligibility_policy=request.eligibility_policy,
    )


def _reused_chronology(validation: _SerializedChronology) -> ChronologyValidation:
    return ChronologyValidation(
        validation.group_identity,
        AvailabilityStatus(validation.status),
        validation.total_rows,
        validation.parseable_rows,
        validation.invalid_rows,
        validation.duplicate_timestamp_count,
        validation.is_monotonic,
        validation.reason,
        validation.temporal_eligible,
        None if validation.evidence_source_path is None else Path(validation.evidence_source_path),
        validation.evidence_row_count,
        validation.alignment_verified,
        validation.alignment_offset_microseconds,
        validation.skipped_evidence_rows,
        validation.trailing_evidence_rows,
    )


def _reused_inventory(dataset: DatasetId, inventory: _SerializedInventory) -> RawDatasetInventory:
    sources = tuple(
        RawSourceFile(
            dataset,
            Path(source.path),
            ByteCount(source.size_bytes),
            Checksum(source.checksum),
            SourceFileRole(source.role),
            source.row_count,
        )
        for source in inventory.sources
    )
    return RawDatasetInventory(
        dataset,
        sources,
        inventory.accepted_source_count,
        inventory.excluded_source_count,
        inventory.accepted_row_count,
        Checksum(inventory.checksum),
    )


def _reused_validation_report(
    dataset: DatasetId,
    report: _SerializedValidationReport,
    inventory: RawDatasetInventory,
) -> DatasetValidationReport:
    issues = tuple(
        DatasetValidationIssue(
            ValidationSeverity(issue.severity),
            DatasetValidationCode(issue.code),
            dataset,
            issue.source_context,
            issue.reason,
            issue.affected_count,
        )
        for issue in report.issues
    )
    exclusions = tuple(_reused_exclusion(dataset, exclusion, inventory) for exclusion in report.exclusions)
    return DatasetValidationReport(
        dataset,
        issues,
        exclusions,
        report.accepted_rows,
        report.excluded_rows,
        report.invalid_rows,
        report.warning_count,
        AvailabilityStatus(report.status),
    )


def _reused_exclusion(
    dataset: DatasetId,
    exclusion: _SerializedExclusion,
    inventory: RawDatasetInventory,
) -> DatasetExclusion:
    source_path = None if exclusion.source_path is None else Path(exclusion.source_path)
    source_row = (
        None
        if exclusion.source_row_index is None
        else SourceRowReference(_reused_inventory_source(inventory, source_path), exclusion.source_row_index)
    )
    return DatasetExclusion(
        dataset,
        source_path,
        source_row,
        ExclusionReason(exclusion.reason),
        exclusion.evidence,
        exclusion.affected_count,
    )


def _reused_inventory_source(inventory: RawDatasetInventory, source_path: Path | None) -> RawSourceFile:
    if source_path is None:
        raise ValueError("row exclusions require a source path")
    for source in inventory.sources:
        if source.relative_path == source_path:
            return source
    raise ValueError("manifest exclusion references an unknown source")


def _source_state_matches(probe: SourceStateProbe) -> bool:
    source_state = probe.target / _SOURCE_STATE_NAME
    try:
        serialized_state = source_state.read_text(encoding="utf-8")
        state = _SerializedSourceState.model_validate_json(serialized_state)
    except (OSError, ValueError):
        return False
    return state == _source_state(probe.dataset, probe.source_paths, probe.manifest, probe.source_path_resolver)


def write_source_state(
    target: Path,
    dataset: DatasetId,
    source_paths: tuple[Path, ...],
    source_path_resolver: SourcePathResolver,
) -> None:
    if not source_paths:
        return
    manifest_path = target / _MANIFEST_NAME
    if not manifest_path.is_file():
        return
    manifest = manifest_path.read_text(encoding="utf-8")
    state_path = target / _SOURCE_STATE_NAME
    temporary = state_path.with_name(f".{_SOURCE_STATE_NAME}")
    temporary.write_text(
        _source_state(dataset, source_paths, manifest, source_path_resolver).model_dump_json(), encoding="utf-8"
    )
    temporary.replace(state_path)


def _source_state(
    dataset: DatasetId,
    source_paths: tuple[Path, ...],
    manifest: str,
    source_path_resolver: SourcePathResolver,
) -> _SerializedSourceState:
    sources = tuple(
        _source_state_entry(path, source_path_resolver)
        for path in sorted(source_paths, key=lambda candidate: candidate.as_posix())
    )
    return _SerializedSourceState(
        content_checksum_verified=True,
        dataset=dataset.value,
        manifest_checksum=sha256(manifest.encode()).hexdigest(),
        sources=sources,
    )


def _source_state_entry(path: Path, source_path_resolver: SourcePathResolver) -> _SerializedSourceStateEntry:
    state = path.stat()
    return _SerializedSourceStateEntry(
        modified_time_nanoseconds=state.st_mtime_ns,
        path=source_path_resolver(path).as_posix(),
        size_bytes=state.st_size,
    )


def _reusable_manifest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    files: PublicationFiles,
    publication: PublicationMatchRequest[AssetRoleT, EligibilityReasonT],
) -> _SerializedManifest | None:
    loaded_manifest = _read_manifest(files.target, files.schema_file, files.manifest_file, files.complete_file)
    if loaded_manifest is None:
        return None
    manifest, serialized_manifest = loaded_manifest
    compatible = _documents_match_publication(
        files.schema_file, files.complete_file, serialized_manifest, publication.schema
    )
    return manifest if compatible and _manifest_matches_publication(manifest, publication) else None


def _read_manifest(
    target: Path, schema_file: Path, manifest_file: Path, complete_file: Path
) -> tuple[_SerializedManifest, str] | None:
    if not _publication_files_exist(target, schema_file, manifest_file, complete_file):
        return None
    try:
        serialized_manifest = manifest_file.read_text(encoding="utf-8")
        return _SerializedManifest.model_validate_json(serialized_manifest), serialized_manifest
    except (OSError, ValueError):
        return None


def _publication_files_exist(target: Path, schema_file: Path, manifest_file: Path, complete_file: Path) -> bool:
    return target.is_dir() and schema_file.is_file() and manifest_file.is_file() and complete_file.is_file()


def _documents_match_publication(
    schema_file: Path, complete_file: Path, serialized_manifest: str, schema: CanonicalSchema
) -> bool:
    serialized_schema = schema_content(schema)
    return schema_file.read_text(encoding="utf-8") == serialized_schema and complete_file.read_text(
        encoding="utf-8"
    ) == complete_content(serialized_manifest, serialized_schema)


def _manifest_matches_publication[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    manifest: _SerializedManifest, publication: PublicationMatchRequest[AssetRoleT, EligibilityReasonT]
) -> bool:
    return (
        manifest.dataset,
        manifest.schema_checksum,
        manifest.canonicalization_contract,
        manifest.inventory,
        manifest.validation_report,
        manifest.chronology,
        manifest.eligibility_policy,
    ) == (
        publication.schema.dataset.value,
        publication.schema.checksum.value,
        publication.canonicalization_contract,
        _serialized_inventory(publication.inventory),
        _serialized_validation_report(publication.validation_report),
        tuple(_serialized_chronology(validation) for validation in publication.chronology),
        _serialized_eligibility_policy(publication.eligibility_policy),
    )


def asset_is_valid(root: Path, asset: _SerializedAsset, expected_physical_schema: str) -> bool:
    try:
        path = canonical_asset_path(root, Path(asset.path))
    except ValueError:
        return False
    if not path.is_file() or file_checksum(path).value != asset.checksum:
        return False
    try:
        parquet = pq.ParquetFile(path)
        return (
            parquet.metadata.num_rows == asset.row_count
            and tuple(parquet.schema_arrow.names) == asset.columns
            and parquet.schema_arrow.to_string(show_field_metadata=True, show_schema_metadata=True)
            == expected_physical_schema
        )
    except (OSError, pa.ArrowInvalid):
        return False


def _assets_have_declared_metadata(
    root: Path, assets: tuple[_SerializedAsset, ...], expected_physical_schema: str
) -> bool:
    return all(_asset_has_declared_metadata(root, asset, expected_physical_schema) for asset in assets)


def _asset_has_declared_metadata(root: Path, asset: _SerializedAsset, expected_physical_schema: str) -> bool:
    try:
        path = canonical_asset_path(root, Path(asset.path))
    except ValueError:
        return False
    if not path.is_file():
        return False
    try:
        parquet = pq.ParquetFile(path)
        return (
            parquet.metadata.num_rows == asset.row_count
            and tuple(parquet.schema_arrow.names) == asset.columns
            and parquet.schema_arrow.to_string(show_field_metadata=True, show_schema_metadata=True)
            == expected_physical_schema
        )
    except (OSError, pa.ArrowInvalid):
        return False


def _serialized_column(column: CanonicalColumn) -> _SerializedColumn:
    return _SerializedColumn(
        dtype=column.dtype.value,
        name=column.name,
        nullable=column.nullable,
        position=column.position,
        role=column.role.value,
        source_name=column.source_name,
    )


def _serialized_source(source: RawSourceFile) -> _SerializedSource:
    return _SerializedSource(
        checksum=source.checksum.value,
        path=source.relative_path.as_posix(),
        role=source.role.value,
        row_count=source.observed_row_count,
        size_bytes=source.size_bytes.value,
    )


def _serialized_inventory(inventory: RawDatasetInventory) -> _SerializedInventory:
    return _SerializedInventory(
        accepted_row_count=inventory.accepted_row_count,
        accepted_source_count=inventory.accepted_source_count,
        checksum=inventory.checksum.value,
        excluded_source_count=inventory.excluded_source_count,
        sources=tuple(_serialized_source(source) for source in inventory.sources),
    )


def _serialized_issue(issue: DatasetValidationIssue) -> _SerializedIssue:
    return _SerializedIssue(
        affected_count=issue.affected_count,
        code=issue.code.value,
        reason=issue.reason,
        severity=issue.severity.value,
        source_context=issue.source_context,
    )


def _serialized_exclusion(exclusion: DatasetExclusion) -> _SerializedExclusion:
    return _SerializedExclusion(
        affected_count=exclusion.affected_count,
        evidence=exclusion.evidence,
        reason=exclusion.reason.value,
        source_path=None if exclusion.source_path is None else exclusion.source_path.as_posix(),
        source_row_index=None if exclusion.source_row is None else exclusion.source_row.zero_based_row_index,
    )


def _serialized_validation_report(report: DatasetValidationReport) -> _SerializedValidationReport:
    return _SerializedValidationReport(
        accepted_rows=report.accepted_rows,
        excluded_rows=report.excluded_rows,
        exclusions=tuple(_serialized_exclusion(exclusion) for exclusion in report.exclusions),
        invalid_rows=report.invalid_rows,
        issues=tuple(_serialized_issue(issue) for issue in report.issues),
        status=report.status.value,
        warning_count=report.warning_count,
    )


def _serialized_eligibility_policy[EligibilityReasonT: StrEnum](
    policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None,
) -> _SerializedEligibilityPolicy | None:
    if policy is None:
        return None
    semantic_content = "\n".join(
        (
            policy.dataset.value,
            policy.label_column,
            *policy.feature_columns,
            *(reason.value for reason in policy.exclusion_reasons),
        )
    )
    return _SerializedEligibilityPolicy(
        checksum=sha256(semantic_content.encode()).hexdigest(),
        feature_columns=policy.feature_columns,
        label_column=policy.label_column,
        reasons=tuple(reason.value for reason in policy.exclusion_reasons),
    )


def serialized_asset[AssetRoleT: StrEnum](asset: CanonicalAsset[AssetRoleT]) -> _SerializedAsset:
    return _SerializedAsset(
        checksum=asset.checksum.value,
        columns=asset.columns,
        path=asset.relative_path.as_posix(),
        row_count=asset.row_count,
        role=asset.role.value,
        source_identity=asset.source_identity,
    )


def _serialized_chronology(validation: ChronologyValidation) -> _SerializedChronology:
    return _SerializedChronology(
        alignment_offset_microseconds=validation.alignment_offset_microseconds,
        alignment_verified=validation.alignment_verified,
        duplicate_timestamp_count=validation.duplicate_timestamp_count,
        evidence_row_count=validation.evidence_row_count,
        evidence_source_path=(
            None if validation.evidence_source_path is None else validation.evidence_source_path.as_posix()
        ),
        group_identity=validation.group_identity,
        invalid_rows=validation.invalid_rows,
        is_monotonic=validation.is_monotonic,
        parseable_rows=validation.parseable_rows,
        reason=validation.reason,
        skipped_evidence_rows=validation.skipped_evidence_rows,
        status=validation.status.value,
        temporal_eligible=validation.temporal_eligible,
        total_rows=validation.total_rows,
        trailing_evidence_rows=validation.trailing_evidence_rows,
    )


@dataclass(frozen=True, slots=True)
class ManifestSerializationRequest[EligibilityReasonT: StrEnum]:
    dataset: DatasetId
    canonicalization_contract: str
    schema_checksum: Checksum
    inventory: RawDatasetInventory
    validation_report: DatasetValidationReport
    chronology: tuple[ChronologyValidation, ...] = ()
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None


def serialized_manifest_json[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    request: ManifestSerializationRequest[EligibilityReasonT],
    assets: tuple[CanonicalAsset[AssetRoleT], ...],
) -> str:
    return _SerializedManifest(
        assets=tuple(serialized_asset(asset) for asset in assets),
        canonicalization_contract=request.canonicalization_contract,
        chronology=tuple(_serialized_chronology(validation) for validation in request.chronology),
        dataset=request.dataset.value,
        eligibility_policy=_serialized_eligibility_policy(request.eligibility_policy),
        inventory=_serialized_inventory(request.inventory),
        schema_checksum=request.schema_checksum.value,
        validation_report=_serialized_validation_report(request.validation_report),
    ).model_dump_json()
