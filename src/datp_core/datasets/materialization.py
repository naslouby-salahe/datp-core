"""Typed, streaming-safe canonical dataset publication."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Protocol

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from filelock import FileLock
from pydantic import BaseModel, ConfigDict, Field

from datp_core.datasets.models import (
    CanonicalAssetRole,
    CanonicalColumn,
    CanonicalColumnRole,
    CanonicalProvenanceColumn,
    CanonicalPublicationArtifact,
    CanonicalSchema,
    ChronologyValidation,
    DatasetExclusion,
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


class CanonicalReuseRequest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](Protocol):
    @property
    def canonical_root(self) -> Path: ...

    @property
    def schema(self) -> CanonicalSchema: ...

    @property
    def canonicalization_contract(self) -> str: ...

    @property
    def source_paths(self) -> tuple[Path, ...]: ...

    @property
    def source_path_resolver(self) -> SourcePathResolver: ...

    @property
    def eligibility_policy(self) -> ModelInputEligibilityPolicy[EligibilityReasonT] | None: ...

    @property
    def asset_role_type(self) -> type[AssetRoleT]: ...


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
        if not _is_canonical_relative_path(self.relative_path) or not self.columns or self.row_count < 0:
            raise ValueError("canonical assets require a relative path, columns, and a non-negative row count")


@dataclass(frozen=True, slots=True)
class CanonicalManifest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum]:
    dataset: DatasetId
    canonicalization_contract: str
    schema_checksum: Checksum
    inventory: RawDatasetInventory
    validation_report: DatasetValidationReport
    assets: tuple[CanonicalAsset[AssetRoleT], ...]
    chronology: tuple[ChronologyValidation, ...] = ()
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None

    def content(self) -> str:
        return _SerializedManifest(
            assets=tuple(_serialized_asset(asset) for asset in self.assets),
            canonicalization_contract=self.canonicalization_contract,
            chronology=tuple(_serialized_chronology(validation) for validation in self.chronology),
            dataset=self.dataset.value,
            eligibility_policy=_serialized_eligibility_policy(self.eligibility_policy),
            inventory=_serialized_inventory(self.inventory),
            schema_checksum=self.schema_checksum.value,
            validation_report=_serialized_validation_report(self.validation_report),
        ).model_dump_json()


@dataclass(frozen=True, slots=True)
class CanonicalPublication[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum]:
    canonical_root: Path
    canonicalization_contract: str
    schema: CanonicalSchema
    inventory: RawDatasetInventory
    validation_report: DatasetValidationReport
    expected_assets: tuple[CanonicalAssetLayout[AssetRoleT], ...]
    writer: Callable[[Path], tuple[CanonicalAsset[AssetRoleT], ...]]
    source_paths: tuple[Path, ...]
    source_path_resolver: SourcePathResolver
    chronology: tuple[ChronologyValidation, ...] = ()
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None

    def __post_init__(self) -> None:
        _validate_publication_records(self)
        _validate_publication_contract(self)
        _validate_publication_eligibility_policy(self)


def _validate_publication_records[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    publication: CanonicalPublication[AssetRoleT, EligibilityReasonT],
) -> None:
    if publication.inventory.dataset is not publication.schema.dataset:
        raise ValueError("canonical inventory must match the schema dataset")
    if publication.validation_report.dataset is not publication.schema.dataset:
        raise ValueError("canonical validation report must match the schema dataset")
    if not publication.expected_assets:
        raise ValueError("canonical publication requires expected assets")


def _validate_publication_contract[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    publication: CanonicalPublication[AssetRoleT, EligibilityReasonT],
) -> None:
    if not publication.canonicalization_contract:
        raise ValueError("canonical publication requires an explicit semantic contract")


def _validate_publication_eligibility_policy[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    publication: CanonicalPublication[AssetRoleT, EligibilityReasonT],
) -> None:
    policy = publication.eligibility_policy
    if policy is not None and policy.dataset is not publication.schema.dataset:
        raise ValueError("canonical eligibility policy must match the published dataset")


def canonical_asset_path(root: Path, relative_path: Path) -> Path:
    if not _is_canonical_relative_path(relative_path):
        raise ValueError("canonical assets must remain below the data branch")
    candidate = root / relative_path
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError("canonical asset path escapes its publication root")
    return candidate


def _is_canonical_relative_path(path: Path) -> bool:
    return not path.is_absolute() and path.parts[:1] == (DATA_ROOT.name,) and ".." not in path.parts


def provenance_expressions(path: Path, source_path_resolver: SourcePathResolver) -> tuple[pl.Expr, ...]:
    relative_path = source_path_resolver(path).as_posix()
    return (
        pl.lit(relative_path).alias(CanonicalProvenanceColumn.SOURCE_PATH),
        pl.concat_str(
            (
                pl.lit(relative_path),
                pl.lit(":"),
                pl.col(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).cast(pl.String),
            )
        ).alias(CanonicalProvenanceColumn.STABLE_ROW_ID),
    )


def raw_source_file(
    dataset: DatasetId,
    path: Path,
    role: SourceFileRole,
    observed_row_count: int | None,
    source_path_resolver: SourcePathResolver,
) -> RawSourceFile:
    return RawSourceFile(
        dataset=dataset,
        relative_path=source_path_resolver(path),
        size_bytes=ByteCount(path.stat().st_size),
        checksum=_file_checksum(path),
        role=role,
        observed_row_count=observed_row_count,
    )


def raw_inventory(dataset: DatasetId, sources: tuple[RawSourceFile, ...]) -> RawDatasetInventory:
    if not sources:
        raise ValueError("raw inventories require at least one accepted source")
    ordered_sources = tuple(sorted(sources, key=lambda source: source.relative_path.as_posix()))
    if tuple(source.dataset for source in ordered_sources) != (dataset,) * len(ordered_sources):
        raise ValueError("raw inventory sources must belong to its dataset")
    total_rows = _inventory_row_count(ordered_sources)
    return RawDatasetInventory(
        dataset=dataset,
        sources=ordered_sources,
        accepted_source_count=len(ordered_sources),
        excluded_source_count=0,
        accepted_row_count=total_rows,
        checksum=_inventory_checksum(ordered_sources),
    )


def _inventory_row_count(sources: tuple[RawSourceFile, ...]) -> int | None:
    representation_sources = tuple(
        source for source in sources if source.role is not SourceFileRole.CHRONOLOGY_EVIDENCE
    )
    if not all(source.observed_row_count is not None for source in representation_sources):
        return None
    return sum(source.observed_row_count for source in representation_sources if source.observed_row_count is not None)


def _inventory_checksum(sources: tuple[RawSourceFile, ...]) -> Checksum:
    digest = sha256()
    for source in sources:
        digest.update(
            "\t".join(
                (
                    source.relative_path.as_posix(),
                    str(source.size_bytes.value),
                    source.checksum.value,
                    source.role.value,
                    "" if source.observed_row_count is None else str(source.observed_row_count),
                )
            ).encode()
        )
        digest.update(b"\n")
    return Checksum(digest.hexdigest())


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


def canonical_schema_checksum(
    dataset: DatasetId, columns: tuple[CanonicalColumn, ...], physical_schema: pa.Schema
) -> Checksum:
    if tuple(column.nullable for column in columns) != tuple(field.nullable for field in physical_schema):
        raise ValueError("canonical column nullability must match the physical schema")
    content = _SchemaChecksumDocument(
        canonicalization_contract=_CANONICAL_PUBLICATION_CONTRACT,
        columns=tuple(_serialized_column(column) for column in columns),
        dataset=dataset.value,
        physical_schema=physical_schema.to_string(show_field_metadata=True, show_schema_metadata=True),
    ).model_dump_json()
    return Checksum(sha256(content.encode()).hexdigest())


def canonical_provenance_column(column: CanonicalProvenanceColumn, position: int) -> CanonicalColumn:
    """Return the canonical declaration for a cross-dataset provenance field."""
    source_name, dtype = _provenance_column_details(column)
    return CanonicalColumn(
        column,
        source_name,
        dtype,
        CanonicalColumnRole.PROVENANCE,
        True,
        position,
    )


def canonical_provenance_arrow_field(column: CanonicalProvenanceColumn) -> pa.Field:
    """Return the physical Arrow field for a cross-dataset provenance field."""
    match column:
        case CanonicalProvenanceColumn.SOURCE_ROW_INDEX:
            return pa.field(column, pa.uint64())
        case CanonicalProvenanceColumn.SOURCE_PATH | CanonicalProvenanceColumn.STABLE_ROW_ID:
            return pa.field(column, pa.large_string())


def _provenance_column_details(column: CanonicalProvenanceColumn) -> tuple[str, str]:
    match column:
        case CanonicalProvenanceColumn.SOURCE_ROW_INDEX:
            return "source row index", "uint64"
        case CanonicalProvenanceColumn.SOURCE_PATH:
            return "raw-root-relative source path", "string"
        case CanonicalProvenanceColumn.STABLE_ROW_ID:
            return "source path and zero-based row index", "string"


def canonical_directory(canonical_root: Path, schema: CanonicalSchema) -> Path:
    return canonical_root / schema.dataset.value


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
        return _reused_materialized_dataset(
            target,
            request.schema,
            manifest,
            request.eligibility_policy,
            request.asset_role_type,
        )


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
            target,
            schema.dataset,
            request.source_paths,
            serialized_manifest,
            request.source_path_resolver,
        ),
    )
    return (manifest, serialized_manifest) if all(compatible) else None


def _reused_materialized_dataset[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    target: Path,
    schema: CanonicalSchema,
    manifest: _SerializedManifest,
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None,
    asset_role_type: type[AssetRoleT],
) -> MaterializedDataset[AssetRoleT, EligibilityReasonT]:
    inventory = _reused_inventory(schema.dataset, manifest.inventory)
    report = _reused_validation_report(schema.dataset, manifest.validation_report, inventory)
    assets = tuple(
        MaterializedCanonicalAsset(
            canonical_asset_path(target, Path(asset.path)).resolve(),
            asset_role_type(asset.role),
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
        eligibility_policy=eligibility_policy,
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


def partition_assets[AssetRoleT: StrEnum](
    partition_count: int,
    branch: Path,
    role: AssetRoleT,
) -> tuple[CanonicalAssetLayout[AssetRoleT], ...]:
    if partition_count < 1:
        raise ValueError("canonical partition publication requires at least one partition")
    return tuple(
        CanonicalAssetLayout(DATA_ROOT / branch / f"part-{index:05d}.parquet", role) for index in range(partition_count)
    )


def canonical_data_partition_assets(partition_count: int) -> tuple[CanonicalAssetLayout[CanonicalAssetRole], ...]:
    """Name the root canonical-data partitions without exposing an empty path branch."""
    if partition_count < 1:
        raise ValueError("canonical partition publication requires at least one partition")
    return tuple(
        CanonicalAssetLayout(DATA_ROOT / f"part-{index:05d}.parquet", CanonicalAssetRole.CANONICAL_DATA)
        for index in range(partition_count)
    )


def named_assets[AssetRoleT: StrEnum](
    branch: Path, role: AssetRoleT, source_identities: tuple[str, ...]
) -> tuple[CanonicalAssetLayout[AssetRoleT], ...]:
    if not source_identities or len(source_identities) != len(frozenset(source_identities)):
        raise ValueError("named canonical assets require unique source identities")
    return tuple(
        CanonicalAssetLayout(DATA_ROOT / branch / f"{source_identity}.parquet", role, source_identity)
        for source_identity in source_identities
    )


def empty_asset[AssetRoleT: StrEnum](branch: Path, role: AssetRoleT) -> CanonicalAssetLayout[AssetRoleT]:
    return CanonicalAssetLayout(DATA_ROOT / branch / "empty.parquet", role)


def stream_parquet[AssetRoleT: StrEnum](
    frame: pl.LazyFrame,
    canonical_root: Path,
    layout: CanonicalAssetLayout[AssetRoleT],
    expected_schema: pa.Schema,
) -> CanonicalAsset[AssetRoleT]:
    destination = canonical_asset_path(canonical_root, layout.relative_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.sink_parquet(destination, compression="zstd", maintain_order=True, sync_on_close="all")
    parquet = pq.ParquetFile(destination)
    actual_schema = parquet.schema_arrow
    if not actual_schema.equals(expected_schema, check_metadata=False):
        raise ValueError("written Parquet schema differs from the declared canonical schema")
    return CanonicalAsset(
        relative_path=layout.relative_path,
        checksum=_file_checksum(destination),
        row_count=parquet.metadata.num_rows,
        columns=tuple(actual_schema.names),
        role=layout.role,
        source_identity=layout.source_identity,
    )


def publish_canonical[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    publication: CanonicalPublication[AssetRoleT, EligibilityReasonT],
) -> MaterializedDataset[AssetRoleT, EligibilityReasonT]:
    target = canonical_directory(publication.canonical_root, publication.schema)
    with FileLock(f"{target}.lock"):
        _remove_stale_temporary_directories(target)
        if _is_reusable(target, publication):
            _write_source_state(
                target,
                publication.schema.dataset,
                publication.source_paths,
                publication.source_path_resolver,
            )
            return _materialized_dataset(target, publication, PublicationStatus.REUSED)
        if target.exists():
            _remove_target(target, publication.canonical_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(mkdtemp(prefix=f".{target.name}.", dir=target.parent))
        try:
            assets = publication.writer(temporary)
            _validate_written_assets(temporary, assets, publication.expected_assets, publication.schema.physical_schema)
            serialized_schema = schema_content(publication.schema)
            (temporary / _SCHEMA_NAME).write_text(serialized_schema, encoding="utf-8")
            serialized_manifest = CanonicalManifest(
                publication.schema.dataset,
                publication.canonicalization_contract,
                publication.schema.checksum,
                publication.inventory,
                publication.validation_report,
                assets,
                publication.chronology,
                publication.eligibility_policy,
            ).content()
            (temporary / _MANIFEST_NAME).write_text(serialized_manifest, encoding="utf-8")
            _write_source_state(
                temporary,
                publication.schema.dataset,
                publication.source_paths,
                publication.source_path_resolver,
            )
            (temporary / _COMPLETE_NAME).write_text(
                _complete_content(serialized_manifest, serialized_schema), encoding="utf-8"
            )
            if not _is_reusable(temporary, publication):
                raise ValueError("canonical publication did not pass complete-asset validation")
            temporary.replace(target)
        except Exception:
            rmtree(temporary, ignore_errors=True)
            raise
    return _materialized_dataset(target, publication, PublicationStatus.PUBLISHED)


def _source_state_matches(
    target: Path,
    dataset: DatasetId,
    source_paths: tuple[Path, ...],
    manifest: str,
    source_path_resolver: SourcePathResolver,
) -> bool:
    source_state = target / _SOURCE_STATE_NAME
    try:
        serialized_state = source_state.read_text(encoding="utf-8")
        state = _SerializedSourceState.model_validate_json(serialized_state)
    except (OSError, ValueError):
        return False
    return state == _source_state(dataset, source_paths, manifest, source_path_resolver)


def _write_source_state(
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


def _is_reusable[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    target: Path, publication: CanonicalPublication[AssetRoleT, EligibilityReasonT]
) -> bool:
    schema_file = target / _SCHEMA_NAME
    manifest_file = target / _MANIFEST_NAME
    complete_file = target / _COMPLETE_NAME
    manifest = _reusable_manifest(target, schema_file, manifest_file, complete_file, publication)
    if manifest is None:
        return False
    if tuple((Path(asset.path), asset.role, asset.source_identity) for asset in manifest.assets) != tuple(
        (layout.relative_path, layout.role.value, layout.source_identity) for layout in publication.expected_assets
    ):
        return False
    return all(_asset_is_valid(target, asset, publication.schema.physical_schema) for asset in manifest.assets)


def _reusable_manifest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    target: Path,
    schema_file: Path,
    manifest_file: Path,
    complete_file: Path,
    publication: CanonicalPublication[AssetRoleT, EligibilityReasonT],
) -> _SerializedManifest | None:
    loaded_manifest = _read_manifest(target, schema_file, manifest_file, complete_file)
    if loaded_manifest is None:
        return None
    manifest, serialized_manifest = loaded_manifest
    compatible = _documents_match_publication(schema_file, complete_file, serialized_manifest, publication.schema)
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
    ) == _complete_content(serialized_manifest, serialized_schema)


def _manifest_matches_publication[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    manifest: _SerializedManifest, publication: CanonicalPublication[AssetRoleT, EligibilityReasonT]
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


def _asset_is_valid(root: Path, asset: _SerializedAsset, expected_physical_schema: str) -> bool:
    try:
        path = canonical_asset_path(root, Path(asset.path))
    except ValueError:
        return False
    if not path.is_file() or _file_checksum(path).value != asset.checksum:
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


def _validate_written_assets[AssetRoleT: StrEnum](
    temporary: Path,
    assets: tuple[CanonicalAsset[AssetRoleT], ...],
    expected_assets: tuple[CanonicalAssetLayout[AssetRoleT], ...],
    expected_physical_schema: str,
) -> None:
    if not _asset_paths_match(assets, expected_assets):
        raise ValueError("canonical writer returned unexpected assets")
    if not _asset_paths_are_unique(assets):
        raise ValueError("canonical writer returned duplicate asset paths")
    if not _written_assets_are_valid(temporary, assets, expected_physical_schema):
        raise ValueError("canonical writer returned an invalid Parquet asset")


def _asset_paths_match[AssetRoleT: StrEnum](
    assets: tuple[CanonicalAsset[AssetRoleT], ...], expected_assets: tuple[CanonicalAssetLayout[AssetRoleT], ...]
) -> bool:
    return tuple((asset.relative_path, asset.role, asset.source_identity) for asset in assets) == tuple(
        (layout.relative_path, layout.role, layout.source_identity) for layout in expected_assets
    )


def _asset_paths_are_unique[AssetRoleT: StrEnum](assets: tuple[CanonicalAsset[AssetRoleT], ...]) -> bool:
    return len(assets) == len(frozenset(asset.relative_path for asset in assets))


def _written_assets_are_valid[AssetRoleT: StrEnum](
    temporary: Path, assets: tuple[CanonicalAsset[AssetRoleT], ...], expected_physical_schema: str
) -> bool:
    return all(_asset_is_valid(temporary, _serialized_asset(asset), expected_physical_schema) for asset in assets)


def _materialized_dataset[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    target: Path,
    publication: CanonicalPublication[AssetRoleT, EligibilityReasonT],
    status: PublicationStatus,
) -> MaterializedDataset[AssetRoleT, EligibilityReasonT]:
    assets = tuple(
        MaterializedCanonicalAsset(
            canonical_asset_path(target, layout.relative_path).resolve(),
            layout.role,
            _asset_row_count(target, layout),
            layout.source_identity,
        )
        for layout in publication.expected_assets
    )
    return MaterializedDataset(
        dataset=publication.schema.dataset,
        canonical_root=target,
        assets=assets,
        manifest_path=target / _MANIFEST_NAME,
        schema=publication.schema,
        row_count=_logical_row_count(publication, assets),
        source_inventory_checksum=publication.inventory.checksum,
        publication_status=status,
        inventory=publication.inventory,
        validation_report=publication.validation_report,
        chronology=publication.chronology,
        eligibility_policy=publication.eligibility_policy,
    )


def _asset_row_count[AssetRoleT: StrEnum](target: Path, layout: CanonicalAssetLayout[AssetRoleT]) -> int:
    return pq.ParquetFile(canonical_asset_path(target, layout.relative_path)).metadata.num_rows


def _logical_row_count[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    publication: CanonicalPublication[AssetRoleT, EligibilityReasonT],
    assets: tuple[MaterializedCanonicalAsset[AssetRoleT], ...],
) -> int:
    if publication.inventory.accepted_row_count is not None:
        return publication.inventory.accepted_row_count
    return sum(asset.row_count for asset in assets if asset.role is CanonicalAssetRole.CANONICAL_DATA)


def _remove_target(target: Path, canonical_root: Path) -> None:
    resolved_target = target.resolve()
    resolved_root = canonical_root.resolve()
    if not resolved_target.is_relative_to(resolved_root):
        raise ValueError("canonical publication target escapes the canonical root")
    rmtree(resolved_target)


def _remove_stale_temporary_directories(target: Path) -> None:
    parent = target.parent.resolve()
    prefix = f".{target.name}."
    for candidate in target.parent.iterdir():
        if not candidate.is_dir():
            continue
        if not candidate.name.startswith(prefix):
            continue
        if candidate.resolve().is_relative_to(parent):
            rmtree(candidate)


def _dataset_anchor(dataset: DatasetId) -> str:
    match dataset:
        case DatasetId.NBAIOT:
            return "N-BaIoT"
        case DatasetId.CICIOT2023:
            return "CIC_IOT_Dataset2023"
        case DatasetId.EDGE_IIOTSET:
            return "Edge-IIoTset"


def _file_checksum(path: Path) -> Checksum:
    digest = sha256()
    with path.open("rb") as source:
        while chunk := source.read(1_048_576):
            digest.update(chunk)
    return Checksum(digest.hexdigest())


def _complete_content(manifest: str, schema: str) -> str:
    return Checksum(sha256(f"{manifest}\n{schema}".encode()).hexdigest()).value


def _serialized_column(column: CanonicalColumn) -> _SerializedColumn:
    return _SerializedColumn(
        dtype=column.dtype,
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
        code=issue.code,
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


def _serialized_asset[AssetRoleT: StrEnum](asset: CanonicalAsset[AssetRoleT]) -> _SerializedAsset:
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
