"""Canonical publication reuse probing, source-state comparison, and domain reconstruction."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from filelock import FileLock

from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.json import canonical_json_text, canonical_value
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CanonicalizationContractName,
    ColumnName,
    ContractSubject,
    DatasetId,
    PhysicalSchemaText,
    PublicationStatus,
    SerializedDocumentText,
    SourceIdentity,
)
from datp_core.core.numeric import ByteCount, RowCount
from datp_core.data.contracts import (
    CanonicalManifestDocument,
    CanonicalPublicationArtifact,
    CanonicalSchema,
    ChronologyValidation,
    DatasetExclusion,
    DatasetValidationIssue,
    DatasetValidationReport,
    ExcludedSourceFile,
    ManifestAssetEntry,
    ManifestChronologyEntry,
    ManifestExclusionEntry,
    ManifestInventoryEntry,
    ManifestSerializationRequest,
    ManifestValidationReportEntry,
    MaterializedCanonicalAsset,
    MaterializedDataset,
    ModelInputEligibilityPolicy,
    RawDatasetInventory,
    RawSourceFile,
    SourceRowReference,
    SourceStateDocument,
    SourceStateEntryDocument,
    complete_digest,
    manifest_chronology_entry,
    manifest_eligibility_entry,
    manifest_inventory_entry,
    manifest_validation_report_entry,
    schema_content,
)

SourcePathResolver = Callable[[Path], Path]


@dataclass(frozen=True, slots=True)
class CanonicalAssetLayout[AssetRoleT: StrEnum]:
    relative_path: Path
    role: AssetRoleT
    source_identity: SourceIdentity | None = None

    def __post_init__(self) -> None:
        if not _is_canonical_relative_path(self.relative_path):
            raise ValueError("canonical asset layouts must use publication-root-relative paths")


@dataclass(frozen=True, slots=True)
class CanonicalAsset[AssetRoleT: StrEnum]:
    relative_path: Path
    checksum: Checksum
    row_count: RowCount
    columns: tuple[ColumnName, ...]
    role: AssetRoleT
    source_identity: SourceIdentity | None = None

    def __post_init__(self) -> None:
        if not _is_canonical_relative_path(self.relative_path):
            raise ValueError("canonical assets require a publication-root-relative path")
        if not self.columns:
            raise ValueError("canonical assets require columns")


def canonical_asset_path(root: Path, relative_path: Path) -> Path:
    if not _is_canonical_relative_path(relative_path):
        raise ValueError("canonical assets must remain below their publication root")
    candidate = root / relative_path
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError("canonical asset path escapes its publication root")
    return candidate


def _is_canonical_relative_path(path: Path) -> bool:
    return bool(path.parts) and not path.is_absolute() and ".." not in path.parts


def canonical_directory(canonical_root: Path, schema: CanonicalSchema) -> Path:
    return canonical_root / schema.dataset.value


@dataclass(frozen=True, slots=True)
class CanonicalReuseRequest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum]:
    canonical_root: Path
    schema: CanonicalSchema
    canonicalization_contract: CanonicalizationContractName
    source_paths: tuple[Path, ...]
    source_path_resolver: SourcePathResolver
    asset_role_type: type[AssetRoleT]
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None


@dataclass(frozen=True, slots=True)
class PublicationMatchRequest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum]:
    schema: CanonicalSchema
    canonicalization_contract: CanonicalizationContractName
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
    manifest: SerializedDocumentText
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
        target / CanonicalPublicationArtifact.SCHEMA,
        target / CanonicalPublicationArtifact.MANIFEST,
        target / CanonicalPublicationArtifact.COMPLETE,
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
) -> tuple[CanonicalManifestDocument, SerializedDocumentText] | None:
    schema = request.schema
    schema_file = target / CanonicalPublicationArtifact.SCHEMA
    manifest_file = target / CanonicalPublicationArtifact.MANIFEST
    complete_file = target / CanonicalPublicationArtifact.COMPLETE
    published_manifest = _read_manifest(target, schema_file, manifest_file, complete_file)
    if published_manifest is None:
        return None
    manifest, serialized_manifest = published_manifest
    compatible = (
        _documents_match_publication(schema_file, complete_file, serialized_manifest, schema),
        manifest.dataset is schema.dataset,
        manifest.schema_checksum == schema.checksum,
        manifest.canonicalization_contract == request.canonicalization_contract,
        canonical_value(manifest.eligibility_policy) == canonical_value(request.eligibility_policy),
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
    manifest: CanonicalManifestDocument,
) -> MaterializedDataset[AssetRoleT, EligibilityReasonT]:
    schema = request.schema
    inventory = _inventory_from_serialized(schema.dataset, manifest.inventory)
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
        manifest_path=target / CanonicalPublicationArtifact.MANIFEST,
        schema=schema,
        row_count=(
            inventory.accepted_row_count
            if inventory.accepted_row_count is not None
            else RowCount(sum(asset.row_count.value for asset in assets))
        ),
        source_inventory_checksum=inventory.checksum,
        publication_status=PublicationStatus.REUSED,
        inventory=inventory,
        validation_report=report,
        chronology=tuple(_chronology_from_serialized(document) for document in manifest.chronology),
        eligibility_policy=request.eligibility_policy,
    )


def _reused_validation_report(
    dataset: DatasetId,
    report: ManifestValidationReportEntry,
    inventory: RawDatasetInventory,
) -> DatasetValidationReport:
    issues = tuple(
        DatasetValidationIssue(
            issue.severity,
            issue.code,
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
        report.status,
    )


def _reused_exclusion(
    dataset: DatasetId,
    exclusion: ManifestExclusionEntry,
    inventory: RawDatasetInventory,
) -> DatasetExclusion:
    source_path = None if exclusion.source_path is None else Path(exclusion.source_path)
    source_row = exclusion.source_row
    source_row_reference = (
        None
        if source_row is None
        else SourceRowReference(_reused_inventory_source(inventory, source_path), source_row.zero_based_row_index)
    )
    return DatasetExclusion(
        dataset,
        source_path,
        source_row_reference,
        exclusion.reason,
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


def _inventory_from_serialized(dataset: DatasetId, inventory: ManifestInventoryEntry) -> RawDatasetInventory:
    sources = tuple(
        RawSourceFile(
            dataset,
            Path(source.relative_path),
            source.size_bytes,
            source.checksum,
            source.role,
            source.observed_row_count,
        )
        for source in inventory.sources
    )
    excluded_sources = tuple(
        ExcludedSourceFile(
            dataset,
            Path(excluded.relative_path),
            excluded.reason,
        )
        for excluded in inventory.excluded_sources
    )
    return RawDatasetInventory(
        dataset,
        sources,
        inventory.accepted_source_count,
        inventory.excluded_source_count,
        excluded_sources,
        inventory.accepted_row_count,
        inventory.checksum,
    )


def _chronology_from_serialized(document: ManifestChronologyEntry) -> ChronologyValidation:
    return ChronologyValidation(
        document.group_identity,
        document.status,
        document.total_rows,
        document.parseable_rows,
        document.invalid_rows,
        document.duplicate_timestamp_count,
        document.is_monotonic,
        document.reason,
        document.temporal_eligible,
        None if document.evidence_source_path is None else Path(document.evidence_source_path),
        document.evidence_row_count,
        document.alignment_verified,
        document.alignment_offset_microseconds,
        document.skipped_evidence_rows,
        document.trailing_evidence_rows,
    )


def _source_state_matches(probe: SourceStateProbe) -> bool:
    source_state = probe.target / CanonicalPublicationArtifact.SOURCE_STATE
    try:
        state = SourceStateDocument.model_validate_json(source_state.read_text(encoding="utf-8"))
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
    manifest_path = target / CanonicalPublicationArtifact.MANIFEST
    if not manifest_path.is_file():
        return
    manifest = SerializedDocumentText(manifest_path.read_text(encoding="utf-8"))
    state_path = target / CanonicalPublicationArtifact.SOURCE_STATE
    temporary = state_path.with_name(f".{CanonicalPublicationArtifact.SOURCE_STATE}")
    temporary.write_text(
        canonical_json_text(_source_state(dataset, source_paths, manifest, source_path_resolver)),
        encoding="utf-8",
    )
    temporary.replace(state_path)


def _source_state(
    dataset: DatasetId,
    source_paths: tuple[Path, ...],
    manifest: SerializedDocumentText,
    source_path_resolver: SourcePathResolver,
) -> SourceStateDocument:
    sources = tuple(
        _source_state_entry(path, source_path_resolver)
        for path in sorted(source_paths, key=lambda candidate: candidate.as_posix())
    )
    return SourceStateDocument(
        content_checksum_verified=True,
        dataset=dataset,
        manifest_checksum=Checksum.from_text(manifest),
        sources=sources,
    )


def _source_state_entry(path: Path, source_path_resolver: SourcePathResolver) -> SourceStateEntryDocument:
    state = path.stat()
    return SourceStateEntryDocument(
        modified_time_nanoseconds=state.st_mtime_ns,
        path=source_path_resolver(path).as_posix(),
        size_bytes=ByteCount(state.st_size),
    )


def _reusable_manifest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    files: PublicationFiles,
    publication: PublicationMatchRequest[AssetRoleT, EligibilityReasonT],
) -> CanonicalManifestDocument | None:
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
) -> tuple[CanonicalManifestDocument, SerializedDocumentText] | None:
    if not _publication_files_exist(target, schema_file, manifest_file, complete_file):
        return None
    try:
        serialized_manifest = SerializedDocumentText(manifest_file.read_text(encoding="utf-8"))
        return CanonicalManifestDocument.model_validate_json(serialized_manifest), serialized_manifest
    except (OSError, ValueError):
        return None


def _publication_files_exist(target: Path, schema_file: Path, manifest_file: Path, complete_file: Path) -> bool:
    return target.is_dir() and schema_file.is_file() and manifest_file.is_file() and complete_file.is_file()


def _documents_match_publication(
    schema_file: Path, complete_file: Path, serialized_manifest: SerializedDocumentText, schema: CanonicalSchema
) -> bool:
    serialized_schema = schema_content(schema)
    return (
        schema_file.read_text(encoding="utf-8") == serialized_schema
        and complete_file.read_text(encoding="utf-8") == complete_digest(serialized_manifest, serialized_schema).value
    )


def _asset_entry[AssetRoleT: StrEnum](asset: CanonicalAsset[AssetRoleT]) -> ManifestAssetEntry:
    return ManifestAssetEntry(
        checksum=asset.checksum,
        columns=asset.columns,
        path=asset.relative_path.as_posix(),
        row_count=asset.row_count,
        role=asset.role.value,
        source_identity=asset.source_identity,
    )


def _manifest_matches_publication[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    manifest: CanonicalManifestDocument, publication: PublicationMatchRequest[AssetRoleT, EligibilityReasonT]
) -> bool:
    expected = CanonicalManifestDocument(
        assets=manifest.assets,
        canonicalization_contract=publication.canonicalization_contract,
        chronology=tuple(manifest_chronology_entry(item) for item in publication.chronology),
        dataset=publication.schema.dataset,
        eligibility_policy=manifest_eligibility_entry(publication.eligibility_policy),
        inventory=manifest_inventory_entry(publication.inventory),
        schema_checksum=publication.schema.checksum,
        validation_report=manifest_validation_report_entry(publication.validation_report),
    )
    return (
        manifest.dataset,
        manifest.schema_checksum,
        manifest.canonicalization_contract,
        manifest.inventory,
        manifest.validation_report,
        manifest.chronology,
        manifest.eligibility_policy,
    ) == (
        expected.dataset,
        expected.schema_checksum,
        expected.canonicalization_contract,
        expected.inventory,
        expected.validation_report,
        expected.chronology,
        expected.eligibility_policy,
    )


def asset_is_valid(root: Path, asset: ManifestAssetEntry, expected_physical_schema: PhysicalSchemaText) -> bool:
    try:
        path = canonical_asset_path(root, Path(asset.path))
    except ValueError:
        return False
    if not path.is_file() or Checksum.from_file(path) != asset.checksum:
        return False
    try:
        parquet = pq.ParquetFile(path)
        return (
            parquet.metadata.num_rows == asset.row_count.value
            and tuple(parquet.schema_arrow.names) == asset.columns
            and parquet.schema_arrow.to_string(show_field_metadata=True, show_schema_metadata=True)
            == expected_physical_schema
        )
    except (OSError, pa.ArrowInvalid):
        return False


def _assets_have_declared_metadata(
    root: Path,
    assets: tuple[ManifestAssetEntry, ...],
    expected_physical_schema: PhysicalSchemaText,
) -> bool:
    return all(_asset_has_declared_metadata(root, asset, expected_physical_schema) for asset in assets)


def _asset_has_declared_metadata(
    root: Path, asset: ManifestAssetEntry, expected_physical_schema: PhysicalSchemaText
) -> bool:
    try:
        path = canonical_asset_path(root, Path(asset.path))
    except ValueError:
        return False
    if not path.is_file():
        return False
    try:
        parquet = pq.ParquetFile(path)
        return (
            parquet.metadata.num_rows == asset.row_count.value
            and tuple(parquet.schema_arrow.names) == tuple(asset.columns)
            and parquet.schema_arrow.to_string(show_field_metadata=True, show_schema_metadata=True)
            == expected_physical_schema
        )
    except (OSError, pa.ArrowInvalid):
        return False


def serialized_asset[AssetRoleT: StrEnum](asset: CanonicalAsset[AssetRoleT]) -> ManifestAssetEntry:
    return _asset_entry(asset)


def serialized_manifest_json[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    request: ManifestSerializationRequest[EligibilityReasonT],
    assets: tuple[CanonicalAsset[AssetRoleT], ...],
) -> SerializedDocumentText:
    return canonical_json_text(
        CanonicalManifestDocument(
            assets=tuple(_asset_entry(asset) for asset in assets),
            canonicalization_contract=request.canonicalization_contract,
            chronology=tuple(manifest_chronology_entry(item) for item in request.chronology),
            dataset=request.dataset,
            eligibility_policy=manifest_eligibility_entry(request.eligibility_policy),
            inventory=manifest_inventory_entry(request.inventory),
            schema_checksum=request.schema_checksum,
            validation_report=manifest_validation_report_entry(request.validation_report),
        )
    )


def require_canonical_publication_complete(
    canonical_root: Path,
    dataset: DatasetId,
    subject: ContractSubject = ContractSubject.PREPROCESSING,
) -> None:
    if not (canonical_root / CanonicalPublicationArtifact.COMPLETE).is_file():
        raise ScientificContractError(
            ErrorMessage(f"canonical COMPLETE marker is required for {dataset.value}"),
            subject=subject,
        )
