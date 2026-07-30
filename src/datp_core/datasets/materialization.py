"""Typed, streaming-safe canonical dataset publication."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from shutil import rmtree

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from datp_core.artifacts.completion import complete_digest
from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.datasets.canonical_cache import (
    CanonicalAsset,
    CanonicalAssetLayout,
    ManifestSerializationRequest,
    PublicationMatchRequest,
    SourcePathResolver,
    canonical_asset_path,
    canonical_directory,
    completed_publication_is_reusable,
    publication_artifact_names,
    schema_checksum_document_json,
    schema_content,
    serialized_manifest_json,
    write_source_state,
)
from datp_core.datasets.models import (
    CanonicalAssetRole,
    CanonicalColumn,
    CanonicalColumnRole,
    CanonicalProvenanceColumn,
    CanonicalSchema,
    ChronologyValidation,
    ColumnLogicalType,
    DatasetValidationReport,
    MaterializedCanonicalAsset,
    MaterializedDataset,
    ModelInputEligibilityPolicy,
    RawDatasetInventory,
    RawSourceFile,
    SourceFileRole,
)
from datp_core.domain.enums import DatasetId, PublicationStatus
from datp_core.domain.values import ByteCount, Checksum, RowCount, checksum_file, checksum_text
from datp_core.protocols.runtime import DATA_ROOT

_COMPLETE_NAME, _MANIFEST_NAME, _SCHEMA_NAME, _SOURCE_STATE_NAME = publication_artifact_names()


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
        return serialized_manifest_json(
            ManifestSerializationRequest(
                dataset=self.dataset,
                canonicalization_contract=self.canonicalization_contract,
                schema_checksum=self.schema_checksum,
                inventory=self.inventory,
                validation_report=self.validation_report,
                chronology=self.chronology,
                eligibility_policy=self.eligibility_policy,
            ),
            self.assets,
        )


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

    def match_request(self) -> PublicationMatchRequest[AssetRoleT, EligibilityReasonT]:
        return PublicationMatchRequest(
            schema=self.schema,
            canonicalization_contract=self.canonicalization_contract,
            inventory=self.inventory,
            validation_report=self.validation_report,
            expected_assets=self.expected_assets,
            chronology=self.chronology,
            eligibility_policy=self.eligibility_policy,
        )


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
    observed_row_count: RowCount | None,
    source_path_resolver: SourcePathResolver,
) -> RawSourceFile:
    return RawSourceFile(
        dataset=dataset,
        relative_path=source_path_resolver(path),
        size_bytes=ByteCount(path.stat().st_size),
        checksum=checksum_file(path),
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


def _inventory_row_count(sources: tuple[RawSourceFile, ...]) -> RowCount | None:
    representation_sources = tuple(
        source for source in sources if source.role is not SourceFileRole.CHRONOLOGY_EVIDENCE
    )
    if not all(source.observed_row_count is not None for source in representation_sources):
        return None
    return RowCount(
        sum(source.observed_row_count.value for source in representation_sources if source.observed_row_count is not None)
    )


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


def canonical_schema_checksum(
    dataset: DatasetId, columns: tuple[CanonicalColumn, ...], physical_schema: pa.Schema
) -> Checksum:
    if tuple(column.nullable for column in columns) != tuple(field.nullable for field in physical_schema):
        raise ValueError("canonical column nullability must match the physical schema")
    content = schema_checksum_document_json(dataset, columns, physical_schema)
    return checksum_text(content)


def canonical_provenance_column(column: CanonicalProvenanceColumn, position: int) -> CanonicalColumn:
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
    match column:
        case CanonicalProvenanceColumn.SOURCE_ROW_INDEX:
            return pa.field(column, pa.uint64())
        case CanonicalProvenanceColumn.SOURCE_PATH | CanonicalProvenanceColumn.STABLE_ROW_ID:
            return pa.field(column, pa.large_string())


def _provenance_column_details(column: CanonicalProvenanceColumn) -> tuple[str, ColumnLogicalType]:
    match column:
        case CanonicalProvenanceColumn.SOURCE_ROW_INDEX:
            return "source row index", ColumnLogicalType.UINT64
        case CanonicalProvenanceColumn.SOURCE_PATH:
            return "raw-root-relative source path", ColumnLogicalType.STRING
        case CanonicalProvenanceColumn.STABLE_ROW_ID:
            return "source path and zero-based row index", ColumnLogicalType.STRING


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
    return partition_assets(partition_count, Path("."), CanonicalAssetRole.CANONICAL_DATA)


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
        checksum=checksum_file(destination),
        row_count=RowCount(parquet.metadata.num_rows),
        columns=tuple(actual_schema.names),
        role=layout.role,
        source_identity=layout.source_identity,
    )


def publish_canonical[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    publication: CanonicalPublication[AssetRoleT, EligibilityReasonT],
) -> MaterializedDataset[AssetRoleT, EligibilityReasonT]:
    target = canonical_directory(publication.canonical_root, publication.schema)
    reused = publish_atomically(
        AtomicPublication(
            target=target,
            overwrite=False,
            is_reusable=lambda directory: completed_publication_is_reusable(directory, publication.match_request()),
            write=lambda temporary: _write_canonical(temporary, publication),
            remove_target=lambda directory: _remove_target(directory, publication.canonical_root),
        )
    )
    if reused:
        write_source_state(
            target,
            publication.schema.dataset,
            publication.source_paths,
            publication.source_path_resolver,
        )
    status = PublicationStatus.REUSED if reused else PublicationStatus.PUBLISHED
    return _materialized_dataset(target, publication, status)


def _write_canonical[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    temporary: Path, publication: CanonicalPublication[AssetRoleT, EligibilityReasonT]
) -> None:
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
    write_source_state(
        temporary,
        publication.schema.dataset,
        publication.source_paths,
        publication.source_path_resolver,
    )
    (temporary / _COMPLETE_NAME).write_text(
        complete_digest(serialized_manifest, serialized_schema).value,
        encoding="utf-8",
    )
    if not completed_publication_is_reusable(temporary, publication.match_request()):
        raise ValueError("canonical publication did not pass complete-asset validation")


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
    from datp_core.datasets.canonical_cache import asset_is_valid, serialized_asset

    if not all(asset_is_valid(temporary, serialized_asset(asset), expected_physical_schema) for asset in assets):
        raise ValueError("canonical writer returned an invalid Parquet asset")


def _asset_paths_match[AssetRoleT: StrEnum](
    assets: tuple[CanonicalAsset[AssetRoleT], ...], expected_assets: tuple[CanonicalAssetLayout[AssetRoleT], ...]
) -> bool:
    return tuple((asset.relative_path, asset.role, asset.source_identity) for asset in assets) == tuple(
        (layout.relative_path, layout.role, layout.source_identity) for layout in expected_assets
    )


def _asset_paths_are_unique[AssetRoleT: StrEnum](assets: tuple[CanonicalAsset[AssetRoleT], ...]) -> bool:
    return len(assets) == len(frozenset(asset.relative_path for asset in assets))


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


def _asset_row_count[AssetRoleT: StrEnum](target: Path, layout: CanonicalAssetLayout[AssetRoleT]) -> RowCount:
    return RowCount(pq.ParquetFile(canonical_asset_path(target, layout.relative_path)).metadata.num_rows)


def _logical_row_count[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    publication: CanonicalPublication[AssetRoleT, EligibilityReasonT],
    assets: tuple[MaterializedCanonicalAsset[AssetRoleT], ...],
) -> RowCount:
    if publication.inventory.accepted_row_count is not None:
        return publication.inventory.accepted_row_count
    return RowCount(sum(asset.row_count.value for asset in assets if asset.role is CanonicalAssetRole.CANONICAL_DATA))


def _remove_target(target: Path, canonical_root: Path) -> None:
    resolved_target = target.resolve()
    resolved_root = canonical_root.resolve()
    if not resolved_target.is_relative_to(resolved_root):
        raise ValueError("canonical publication target escapes the canonical root")
    rmtree(resolved_target)
