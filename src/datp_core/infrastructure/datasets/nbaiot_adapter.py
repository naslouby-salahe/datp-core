"""N-BaIoT dataset adapter implementing the DatasetMaterializer port."""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.application.ports import MaterializationPayload, SourceInventory
from datp_core.domain.datasets import (
    AdapterKind,
    DatasetMaterialization,
    DatasetSetup,
    ResolvedDataset,
)
from datp_core.infrastructure.datasets.nbaiot import (
    consolidate_nbaiot_parquet_sources,
    write_nbaiot_source_parquet,
)
from datp_core.infrastructure.tables.parquet_io import normalize_materialized_parquet


@define(frozen=True, slots=True, kw_only=True)
class NBaIoTMaterializationPayload:
    """Staged N-BaIoT materialization result."""

    staged_path: Path
    row_count: int
    preprocessing_evidence: bytes


class NBaIoTAdapter:
    """N-BaIoT dataset materializer: path-derived identity, chronological split, Parquet output."""

    @property
    def adapter_kind(self) -> AdapterKind:
        return AdapterKind.NBAIOT

    def materialize(
        self,
        dataset: ResolvedDataset,
        setup: DatasetSetup,
        materialization: DatasetMaterialization,
        inventory: SourceInventory,
        staging_root: Path,
    ) -> MaterializationPayload:
        inspection = dataset.inspection_contract
        if inspection.benign_filename is None:
            raise ValueError("N-BaIoT configured benign filename is absent")

        primary_tree = inspection.source_trees[0]
        feature_headers = primary_tree.required_headers
        attack_family_directories = inspection.attack_family_directories
        dataset_root = dataset.paths.raw_root.resolve()
        chunk_row_count = 100_000  # Default; overridden by runtime profile if needed

        staged_files: list[Path] = []
        for source_index, entry in enumerate(inventory.entries):
            staged_file = staging_root / f"source_{source_index:04d}.parquet"
            write_nbaiot_source_parquet(
                entry.source_path,
                staged_file,
                dataset_root,
                feature_headers,
                inspection.benign_filename,
                attack_family_directories,
                materialization,
                chunk_row_count,
            )
            staged_files.append(staged_file)

        unprocessed_payload = staging_root / "unprocessed.parquet"
        total_rows = consolidate_nbaiot_parquet_sources(tuple(staged_files), unprocessed_payload, chunk_row_count)
        payload_file = staging_root / "materialized.parquet"
        feature_columns = dataset.field_schema.model_features
        if feature_columns is None:
            raise ValueError("N-BaIoT materialization requires configured model features")
        normalization = normalize_materialized_parquet(
            unprocessed_payload,
            payload_file,
            feature_columns=feature_columns.order,
            strategy=materialization.normalization_strategy,
            scope=materialization.normalization_scope,
        )

        return NBaIoTMaterializationPayload(
            staged_path=payload_file,
            row_count=total_rows,
            preprocessing_evidence=normalization.encode(),
        )
