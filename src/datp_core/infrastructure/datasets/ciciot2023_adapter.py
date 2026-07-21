"""CICIoT2023 dataset adapter implementing the DatasetMaterializer port."""

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
from datp_core.infrastructure.datasets.ciciot2023 import write_ciciot2023_materialized_parquet


@define(frozen=True, slots=True, kw_only=True)
class CICIoT2023MaterializationPayload:
    """Staged CICIoT2023 materialization result."""

    staged_path: Path
    row_count: int


class CICIoT2023Adapter:
    """CICIoT2023 dataset materializer: merged-source pseudo-client, dedup, random split, Parquet output."""

    @property
    def adapter_kind(self) -> AdapterKind:
        return AdapterKind.CICIOT2023

    def materialize(
        self,
        dataset: ResolvedDataset,
        setup: DatasetSetup,
        materialization: DatasetMaterialization,
        inventory: SourceInventory,
        staging_root: Path,
    ) -> MaterializationPayload:
        inspection = dataset.inspection_contract
        if inspection.benign_label is None:
            raise ValueError("CICIoT2023 configured benign label is absent")

        primary_tree = inspection.source_trees[0]
        feature_headers = primary_tree.required_headers[:-1]
        label_header = primary_tree.required_headers[-1]
        merged_root = dataset.paths.raw_data_root / primary_tree.root.value
        chunk_row_count = 100_000

        source_paths = tuple(entry.source_path for entry in inventory.entries)
        payload_file = staging_root / "materialized.parquet"

        report = write_ciciot2023_materialized_parquet(
            source_paths,
            payload_file,
            feature_headers,
            label_header,
            merged_root.resolve(),
            inspection.benign_label,
            materialization,
            chunk_row_count,
        )

        return CICIoT2023MaterializationPayload(staged_path=payload_file, row_count=report.written_rows)
