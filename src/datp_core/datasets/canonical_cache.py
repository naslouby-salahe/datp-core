"""Canonical publication reuse, source-state comparison, and manifest serialization."""

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import fields as dc_fields
from enum import StrEnum
from json import dumps
from pathlib import Path
from typing import cast

import pyarrow as pa
import pyarrow.parquet as pq
from filelock import FileLock

from datp_core.artifacts.completion import complete_digest
from datp_core.datasets.models import (
    CanonicalAssetRole,
    CanonicalColumn,
    CanonicalManifestDocument,
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
    RawDatasetInventory,
    RawSourceFile,
    SourceFileRole,
    SourceRowReference,
    SourceStateDocument,
    SourceStateEntryDocument,
    ValidationSeverity,
    _AssetEntry,
    _ChronologyEntry,
    _EligibilityPolicyEntry,
    _InventoryEntry,
    _ValidationReportEntry,
)
from datp_core.domain.enums import AvailabilityStatus, ContractSubject, DatasetId, PublicationStatus
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import ByteCount, Checksum, RowCount, checksum_file, checksum_text
from datp_core.protocols.runtime import DATA_ROOT

_CANONICAL_PUBLICATION_CONTRACT = "canonical_publication_contract"
_COMPLETE_NAME = CanonicalPublicationArtifact.COMPLETE
_MANIFEST_NAME = CanonicalPublicationArtifact.MANIFEST
_SCHEMA_NAME = CanonicalPublicationArtifact.SCHEMA
_SOURCE_STATE_NAME = CanonicalPublicationArtifact.SOURCE_STATE

SourcePathResolver = Callable[[Path], Path]


def _serialize(obj):
    if obj is None:
        return None
    if isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, StrEnum):
        return obj.value
    if isinstance(obj, tuple):
        return tuple(_serialize(item) for item in obj)
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _serialize(value) for key, value in obj.items()}
    if isinstance(obj, Path):
        return obj.as_posix()
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "__dataclass_fields__"):
        own_fields = dc_fields(obj)
        if len(own_fields) == 1 and own_fields[0].name == "value":
            return obj.value
        return {field.name: _serialize(getattr(obj, field.name)) for field in own_fields}
    raise TypeError(f"cannot serialize {type(obj)}")


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
    row_count: RowCount
    columns: tuple[str, ...]
    role: AssetRoleT
    source_identity: str | None = None

    def __post_init__(self) -> None:
        if not _is_canonical_relative_path(self.relative_path):
            raise ValueError("canonical assets require a relative path and columns")
        if not self.columns:
            raise ValueError("canonical assets require a relative path and columns")

    def serialize(self) -> dict[str, str | tuple[str, ...] | int | None]:
        return {
            "checksum": self.checksum.value,
            "columns": self.columns,
            "path": self.relative_path.as_posix(),
            "row_count": self.row_count.value,
            "role": self.role.value,
            "source_identity": self.source_identity,
        }


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
    return dumps(_serialize(schema), sort_keys=True)


def schema_checksum_document_json(
    dataset: DatasetId, columns: tuple[CanonicalColumn, ...], physical_schema: pa.Schema
) -> str:
    return dumps(
        {
            "canonicalization_contract": _CANONICAL_PUBLICATION_CONTRACT,
            "columns": [_serialize(column) for column in columns],
            "dataset": dataset.value,
            "physical_schema": physical_schema.to_string(show_field_metadata=True, show_schema_metadata=True),
        },
        sort_keys=True,
    )


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


@dataclass(frozen=True, slots=True)
class ManifestSerializationRequest[EligibilityReasonT: StrEnum]:
    dataset: DatasetId
    canonicalization_contract: str
    schema_checksum: Checksum
    inventory: RawDatasetInventory
    validation_report: DatasetValidationReport
    chronology: tuple[ChronologyValidation, ...] = ()
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None


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
) -> tuple[CanonicalManifestDocument, str] | None:
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
        manifest.dataset is schema.dataset,
        manifest.schema_checksum == schema.checksum.value,
        manifest.canonicalization_contract == request.canonicalization_contract,
        manifest.eligibility_policy == _serialize(request.eligibility_policy),
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
            RowCount(asset.row_count),
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
            else RowCount(
                sum(asset.row_count.value for asset in assets if asset.role is CanonicalAssetRole.CANONICAL_DATA)
            )
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
    report,
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
        RowCount(report.accepted_rows),
        RowCount(report.excluded_rows),
        RowCount(report.invalid_rows),
        report.warning_count,
        AvailabilityStatus(report.status),
    )


def _reused_exclusion(
    dataset: DatasetId,
    exclusion,
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


def _inventory_from_serialized(dataset: DatasetId, inventory) -> RawDatasetInventory:
    sources = tuple(
        RawSourceFile(
            dataset,
            Path(source.relative_path),
            ByteCount(source.size_bytes),
            Checksum(source.checksum),
            SourceFileRole(source.role),
            RowCount(source.observed_row_count) if source.observed_row_count is not None else None,
        )
        for source in inventory.sources
    )
    return RawDatasetInventory(
        dataset,
        sources,
        inventory.accepted_source_count,
        inventory.excluded_source_count,
        RowCount(inventory.accepted_row_count) if inventory.accepted_row_count is not None else None,
        Checksum(inventory.checksum),
    )


def _chronology_from_serialized(document) -> ChronologyValidation:
    return ChronologyValidation(
        document.group_identity,
        AvailabilityStatus(document.status),
        RowCount(document.total_rows),
        RowCount(document.parseable_rows),
        RowCount(document.invalid_rows),
        document.duplicate_timestamp_count,
        document.is_monotonic,
        document.reason,
        document.temporal_eligible,
        None if document.evidence_source_path is None else Path(document.evidence_source_path),
        RowCount(document.evidence_row_count) if document.evidence_row_count is not None else None,
        document.alignment_verified,
        document.alignment_offset_microseconds,
        RowCount(document.skipped_evidence_rows),
        RowCount(document.trailing_evidence_rows),
    )


def _source_state_matches(probe: SourceStateProbe) -> bool:
    source_state = probe.target / _SOURCE_STATE_NAME
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
) -> SourceStateDocument:
    sources = tuple(
        _source_state_entry(path, source_path_resolver)
        for path in sorted(source_paths, key=lambda candidate: candidate.as_posix())
    )
    return SourceStateDocument(
        content_checksum_verified=True,
        dataset=dataset,
        manifest_checksum=checksum_text(manifest).value,
        sources=sources,
    )


def _source_state_entry(path: Path, source_path_resolver: SourcePathResolver) -> SourceStateEntryDocument:
    state = path.stat()
    return SourceStateEntryDocument(
        modified_time_nanoseconds=state.st_mtime_ns,
        path=source_path_resolver(path).as_posix(),
        size_bytes=state.st_size,
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
) -> tuple[CanonicalManifestDocument, str] | None:
    if not _publication_files_exist(target, schema_file, manifest_file, complete_file):
        return None
    try:
        serialized_manifest = manifest_file.read_text(encoding="utf-8")
        return CanonicalManifestDocument.model_validate_json(serialized_manifest), serialized_manifest
    except (OSError, ValueError):
        return None


def _publication_files_exist(target: Path, schema_file: Path, manifest_file: Path, complete_file: Path) -> bool:
    return target.is_dir() and schema_file.is_file() and manifest_file.is_file() and complete_file.is_file()


def _documents_match_publication(
    schema_file: Path, complete_file: Path, serialized_manifest: str, schema: CanonicalSchema
) -> bool:
    serialized_schema = schema_content(schema)
    return (
        schema_file.read_text(encoding="utf-8") == serialized_schema
        and complete_file.read_text(encoding="utf-8") == complete_digest(serialized_manifest, serialized_schema).value
    )


def _manifest_matches_publication[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    manifest: CanonicalManifestDocument, publication: PublicationMatchRequest[AssetRoleT, EligibilityReasonT]
) -> bool:
    expected = CanonicalManifestDocument(
        assets=manifest.assets,
        canonicalization_contract=publication.canonicalization_contract,
        chronology=cast(
            "tuple[_ChronologyEntry, ...]",
            tuple(_serialize(item) for item in publication.chronology),
        ),
        dataset=publication.schema.dataset,
        eligibility_policy=cast("_EligibilityPolicyEntry | None", _serialize(publication.eligibility_policy)),
        inventory=cast("_InventoryEntry", _serialize(publication.inventory)),
        schema_checksum=publication.schema.checksum.value,
        validation_report=cast("_ValidationReportEntry", _serialize(publication.validation_report)),
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


def _asset_field(asset, name: str):
    """Read a field from either a Pydantic model or a plain dict."""
    return asset[name] if isinstance(asset, dict) else getattr(asset, name)


def asset_is_valid(root: Path, asset, expected_physical_schema: str) -> bool:
    try:
        path = canonical_asset_path(root, Path(_asset_field(asset, "path")))
    except ValueError:
        return False
    if not path.is_file() or checksum_file(path).value != _asset_field(asset, "checksum"):
        return False
    try:
        parquet = pq.ParquetFile(path)
        return (
            parquet.metadata.num_rows == _asset_field(asset, "row_count")
            and tuple(parquet.schema_arrow.names) == tuple(_asset_field(asset, "columns"))
            and parquet.schema_arrow.to_string(show_field_metadata=True, show_schema_metadata=True)
            == expected_physical_schema
        )
    except (OSError, pa.ArrowInvalid):
        return False


def _assets_have_declared_metadata(root: Path, assets, expected_physical_schema: str) -> bool:
    return all(_asset_has_declared_metadata(root, asset, expected_physical_schema) for asset in assets)


def _asset_has_declared_metadata(root: Path, asset, expected_physical_schema: str) -> bool:
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
            and tuple(parquet.schema_arrow.names) == tuple(asset.columns)
            and parquet.schema_arrow.to_string(show_field_metadata=True, show_schema_metadata=True)
            == expected_physical_schema
        )
    except (OSError, pa.ArrowInvalid):
        return False


def serialized_asset[AssetRoleT: StrEnum](asset: CanonicalAsset[AssetRoleT]) -> dict:
    return asset.serialize()


def serialized_manifest_json[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    request: ManifestSerializationRequest[EligibilityReasonT],
    assets: tuple[CanonicalAsset[AssetRoleT], ...],
) -> str:
    return CanonicalManifestDocument(
        assets=cast(
            "tuple[_AssetEntry, ...]",
            tuple(asset.serialize() for asset in assets),
        ),
        canonicalization_contract=request.canonicalization_contract,
        chronology=cast(
            "tuple[_ChronologyEntry, ...]",
            tuple(_serialize(item) for item in request.chronology),
        ),
        dataset=request.dataset,
        eligibility_policy=cast("_EligibilityPolicyEntry | None", _serialize(request.eligibility_policy)),
        inventory=cast("_InventoryEntry", _serialize(request.inventory)),
        schema_checksum=request.schema_checksum.value,
        validation_report=cast("_ValidationReportEntry", _serialize(request.validation_report)),
    ).model_dump_json()


def require_canonical_publication_complete(
    canonical_root: Path,
    dataset: DatasetId,
    subject: ContractSubject = ContractSubject.PREPROCESSING,
) -> None:
    if not (canonical_root / CanonicalPublicationArtifact.COMPLETE).is_file():
        raise ScientificContractError(
            "canonical COMPLETE marker is required",
            subject=subject,
        )
