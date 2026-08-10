from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.identifiers import (
    CanonicalAssetRoleToken,
    CanonicalizationContractName,
    CanonicalSourcePath,
    ColumnName,
    DatasetId,
    PhysicalSchemaText,
    SourceIdentity,
)
from datp_core.core.numeric import ByteCount, CanonicalColumnPosition, LogicalElementCount, RowCount, SourceFileCount
from datp_core.data.contracts import (
    CanonicalAssetRole,
    CanonicalColumn,
    CanonicalColumnRole,
    CanonicalManifestDocument,
    CanonicalProvenanceColumn,
    CanonicalSchema,
    ChronologyValidation,
    ColumnLogicalType,
    DatasetValidationReport,
    ExcludedSourceFile,
    ExclusionReason,
    ManifestAssetEntry,
    MaterializedCanonicalAsset,
    MaterializedDataset,
    ModelInputEligibilityPolicy,
    RawDatasetInventory,
    RawSourceFile,
    SourceFileRole,
    manifest_chronology_entry,
    manifest_eligibility_entry,
    manifest_inventory_entry,
    manifest_validation_report_entry,
    schema_content,
)
from datp_core.runtime.filesystem import cleanup_staging_on_failure, create_staging_directory, replace_directory


@dataclass(frozen=True, slots=True)
class CanonicalAssetLayout[AssetRoleT: StrEnum]:
    relative_path: Path
    role: AssetRoleT
    source_identity: SourceIdentity | None = None

    def __post_init__(self) -> None:
        if not _is_relative_path(self.relative_path):
            raise ValueError("canonical assets must use publication-root-relative paths")


@dataclass(frozen=True, slots=True)
class CanonicalAsset[AssetRoleT: StrEnum]:
    relative_path: Path
    row_count: RowCount
    columns: tuple[ColumnName, ...]
    role: AssetRoleT
    source_identity: SourceIdentity | None = None

    def __post_init__(self) -> None:
        if not _is_relative_path(self.relative_path):
            raise ValueError("canonical assets must use publication-root-relative paths")
        if not self.columns:
            raise ValueError("canonical assets require columns")


@dataclass(frozen=True, slots=True)
class CanonicalPublication[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum]:
    canonical_root: Path
    canonicalization_contract: CanonicalizationContractName
    schema: CanonicalSchema
    inventory: RawDatasetInventory
    validation_report: DatasetValidationReport
    expected_assets: tuple[CanonicalAssetLayout[AssetRoleT], ...]
    writer: Callable[[Path], tuple[CanonicalAsset[AssetRoleT], ...]]
    chronology: tuple[ChronologyValidation, ...] = ()
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None

    def __post_init__(self) -> None:
        if self.inventory.dataset is not self.schema.dataset:
            raise ValueError("canonical inventory must match the schema dataset")
        if self.validation_report.dataset is not self.schema.dataset:
            raise ValueError("canonical validation report must match the schema dataset")
        if not self.expected_assets:
            raise ValueError("canonical publication requires expected assets")


def canonical_directory(canonical_root: Path, schema: CanonicalSchema) -> Path:
    return canonical_root / schema.dataset.value


def canonical_asset_path(root: Path, relative_path: Path) -> Path:
    if not _is_relative_path(relative_path):
        raise ValueError("canonical asset path escapes its publication root")
    path = root / relative_path
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("canonical asset path escapes its publication root")
    return path


def require_canonical_dataset(root: Path, dataset: DatasetId) -> None:
    if not (root / "dataset_manifest.json").is_file():
        raise FileNotFoundError(f"canonical dataset is unavailable: {dataset.value}")


def provenance_expressions(path: Path, source_path_resolver: Callable[[Path], Path]) -> tuple[pl.Expr, ...]:
    relative_path = source_path_resolver(path).as_posix()
    return (
        pl.lit(relative_path).alias(CanonicalProvenanceColumn.SOURCE_PATH),
        pl.concat_str(
            (pl.lit(relative_path), pl.lit(":"), pl.col(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).cast(pl.String))
        ).alias(CanonicalProvenanceColumn.STABLE_ROW_ID),
    )


def raw_source_file(
    dataset: DatasetId,
    path: Path,
    role: SourceFileRole,
    observed_row_count: RowCount | None,
    source_path_resolver: Callable[[Path], Path],
) -> RawSourceFile:
    return RawSourceFile(dataset, source_path_resolver(path), ByteCount(path.stat().st_size), role, observed_row_count)


def excluded_source_file(
    dataset: DatasetId, path: Path, reason: ExclusionReason, source_path_resolver: Callable[[Path], Path]
) -> ExcludedSourceFile:
    return ExcludedSourceFile(dataset, source_path_resolver(path), reason)


def raw_inventory(
    dataset: DatasetId,
    sources: tuple[RawSourceFile, ...],
    *,
    excluded_sources: tuple[ExcludedSourceFile, ...] = (),
) -> RawDatasetInventory:
    if not sources:
        raise ValueError("raw inventories require at least one accepted source")
    ordered_sources = tuple(sorted(sources, key=lambda source: source.relative_path.as_posix()))
    ordered_excluded = tuple(sorted(excluded_sources, key=lambda source: source.relative_path.as_posix()))
    return RawDatasetInventory(
        dataset,
        ordered_sources,
        SourceFileCount(len(ordered_sources)),
        SourceFileCount(len(ordered_excluded)),
        ordered_excluded,
        _inventory_row_count(ordered_sources),
    )


def canonical_provenance_column(
    column: CanonicalProvenanceColumn, position: CanonicalColumnPosition
) -> CanonicalColumn:
    match column:
        case CanonicalProvenanceColumn.SOURCE_ROW_INDEX:
            name, dtype = ColumnName("source row index"), ColumnLogicalType.UINT64
        case CanonicalProvenanceColumn.SOURCE_PATH:
            name, dtype = ColumnName("raw-root-relative source path"), ColumnLogicalType.STRING
        case CanonicalProvenanceColumn.STABLE_ROW_ID:
            name, dtype = ColumnName("source path and zero-based row index"), ColumnLogicalType.STRING
    return CanonicalColumn(ColumnName(column), name, dtype, CanonicalColumnRole.PROVENANCE, True, position)


def canonical_provenance_arrow_field(column: CanonicalProvenanceColumn) -> pa.Field:
    match column:
        case CanonicalProvenanceColumn.SOURCE_ROW_INDEX:
            return pa.field(column, pa.uint64())
        case CanonicalProvenanceColumn.SOURCE_PATH | CanonicalProvenanceColumn.STABLE_ROW_ID:
            return pa.field(column, pa.large_string())


def partition_assets[AssetRoleT: StrEnum](
    partition_count: LogicalElementCount, branch: Path, role: AssetRoleT
) -> tuple[CanonicalAssetLayout[AssetRoleT], ...]:
    return tuple(
        CanonicalAssetLayout(branch / f"part-{index:05d}.parquet", role) for index in range(partition_count.value)
    )


def canonical_data_partition_assets(
    partition_count: LogicalElementCount,
) -> tuple[CanonicalAssetLayout[CanonicalAssetRole], ...]:
    return partition_assets(partition_count, Path("data"), CanonicalAssetRole.CANONICAL_DATA)


def named_assets[AssetRoleT: StrEnum](
    branch: Path, role: AssetRoleT, source_identities: tuple[SourceIdentity, ...]
) -> tuple[CanonicalAssetLayout[AssetRoleT], ...]:
    if not source_identities or len(source_identities) != len(frozenset(source_identities)):
        raise ValueError("named canonical assets require unique source identities")
    return tuple(
        CanonicalAssetLayout(branch / f"{source_identity}.parquet", role, source_identity)
        for source_identity in source_identities
    )


def empty_asset[AssetRoleT: StrEnum](branch: Path, role: AssetRoleT) -> CanonicalAssetLayout[AssetRoleT]:
    return CanonicalAssetLayout(branch / "empty.parquet", role)


def stream_parquet[AssetRoleT: StrEnum](
    frame: pl.LazyFrame, canonical_root: Path, layout: CanonicalAssetLayout[AssetRoleT], expected_schema: pa.Schema
) -> CanonicalAsset[AssetRoleT]:
    destination = canonical_asset_path(canonical_root, layout.relative_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.sink_parquet(destination, compression="zstd", maintain_order=True, sync_on_close="all")
    parquet = pq.ParquetFile(destination)
    actual_schema = parquet.schema_arrow
    if not actual_schema.equals(expected_schema, check_metadata=False):
        raise ValueError("written Parquet schema differs from the declared canonical schema")
    return CanonicalAsset(
        layout.relative_path,
        RowCount(parquet.metadata.num_rows),
        tuple(ColumnName(name) for name in actual_schema.names),
        layout.role,
        layout.source_identity,
    )


def publish_canonical[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    publication: CanonicalPublication[AssetRoleT, EligibilityReasonT],
) -> MaterializedDataset[AssetRoleT, EligibilityReasonT]:
    target = canonical_directory(publication.canonical_root, publication.schema)
    temporary = create_staging_directory(target)
    with cleanup_staging_on_failure(temporary):
        assets = publication.writer(temporary)
        _validate_written_assets(temporary, assets, publication.expected_assets, publication.schema.physical_schema)
        (temporary / "schema.json").write_text(schema_content(publication.schema), encoding="utf-8")
        manifest = CanonicalManifestDocument(
            assets=tuple(
                ManifestAssetEntry(
                    columns=asset.columns,
                    path=CanonicalSourcePath(asset.relative_path.as_posix()),
                    row_count=asset.row_count,
                    role=CanonicalAssetRoleToken(asset.role.value),
                    source_identity=asset.source_identity,
                )
                for asset in assets
            ),
            canonicalization_contract=publication.canonicalization_contract,
            chronology=tuple(manifest_chronology_entry(item) for item in publication.chronology),
            dataset=publication.schema.dataset,
            eligibility_policy=manifest_eligibility_entry(publication.eligibility_policy),
            inventory=manifest_inventory_entry(publication.inventory),
            validation_report=manifest_validation_report_entry(publication.validation_report),
        )
        (temporary / "dataset_manifest.json").write_text(canonical_json_text(manifest), encoding="utf-8")
        replace_directory(temporary, target)
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
        publication.schema.dataset,
        target,
        assets,
        target / "dataset_manifest.json",
        publication.schema,
        _logical_row_count(publication, assets),
        publication.inventory,
        publication.validation_report,
        publication.chronology,
        publication.eligibility_policy,
    )


def _is_relative_path(path: Path) -> bool:
    return bool(path.parts) and not path.is_absolute() and ".." not in path.parts


def _inventory_row_count(sources: tuple[RawSourceFile, ...]) -> RowCount | None:
    sources = tuple(source for source in sources if source.role is not SourceFileRole.CHRONOLOGY_EVIDENCE)
    if not all(source.observed_row_count is not None for source in sources):
        return None
    return RowCount(sum(source.observed_row_count.value for source in sources if source.observed_row_count is not None))


def _validate_written_assets[AssetRoleT: StrEnum](
    root: Path,
    assets: tuple[CanonicalAsset[AssetRoleT], ...],
    expected_assets: tuple[CanonicalAssetLayout[AssetRoleT], ...],
    expected_schema: PhysicalSchemaText,
) -> None:
    if tuple((asset.relative_path, asset.role, asset.source_identity) for asset in assets) != tuple(
        (asset.relative_path, asset.role, asset.source_identity) for asset in expected_assets
    ):
        raise ValueError("canonical writer returned unexpected assets")
    if len(assets) != len(frozenset(asset.relative_path for asset in assets)):
        raise ValueError("canonical writer returned duplicate asset paths")
    for asset in assets:
        parquet = pq.ParquetFile(canonical_asset_path(root, asset.relative_path))
        if parquet.metadata.num_rows != asset.row_count.value:
            raise ValueError("canonical asset row count does not match its Parquet data")
        if (
            PhysicalSchemaText(parquet.schema_arrow.to_string(show_field_metadata=True, show_schema_metadata=True))
            != expected_schema
        ):
            raise ValueError("canonical asset schema does not match its declared schema")


def _asset_row_count[AssetRoleT: StrEnum](target: Path, layout: CanonicalAssetLayout[AssetRoleT]) -> RowCount:
    return RowCount(pq.ParquetFile(canonical_asset_path(target, layout.relative_path)).metadata.num_rows)


def _logical_row_count[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum](
    publication: CanonicalPublication[AssetRoleT, EligibilityReasonT],
    assets: tuple[MaterializedCanonicalAsset[AssetRoleT], ...],
) -> RowCount:
    if publication.inventory.accepted_row_count is not None:
        return publication.inventory.accepted_row_count
    return RowCount(sum(asset.row_count.value for asset in assets))
