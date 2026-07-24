"""CICIoT2023 adapter entry point — orchestration only."""

from __future__ import annotations

from pathlib import Path

from datp_core.data.adapters.ciciot2023.index import write_ciciot2023_materialized_parquet
from datp_core.data.contracts.dataset import DatasetSetup, ResolvedDataset
from datp_core.data.contracts.enums import AdapterKind
from datp_core.data.contracts.materialization import DatasetMaterialization, PartitionSeedContract
from datp_core.data.materialization.models import MaterializationResult
from datp_core.data.materialization.ports import SourceInventory
from datp_core.data.preprocessing.normalization import normalize_materialized_parquet
from datp_core.experiments import SweepConditionRecord


class CICIoT2023Adapter:
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
        partition_condition: SweepConditionRecord | None,
        partition_seed_contract: PartitionSeedContract | None,
        *,
        chunk_row_count: int,
    ) -> MaterializationResult:
        if partition_condition is not None or partition_seed_contract is not None:
            raise ValueError("CICIoT2023 does not support partition-condition materialization")
        inspection = dataset.inspection_contract
        if inspection.benign_label is None:
            raise ValueError("CICIoT2023 configured benign label is absent")

        primary_tree = inspection.source_trees[0]
        feature_headers = primary_tree.required_headers[:-1]
        label_header = primary_tree.required_headers[-1]
        merged_root = dataset.paths.raw_data_root / primary_tree.root.value

        source_paths = tuple(entry.source_path for entry in inventory.entries)
        unprocessed_payload = staging_root / "unprocessed.parquet"

        report = write_ciciot2023_materialized_parquet(
            source_paths,
            unprocessed_payload,
            feature_headers,
            label_header,
            merged_root.resolve(),
            inspection.benign_label,
            materialization,
            chunk_row_count,
        )

        feature_columns = dataset.field_schema.model_features
        if feature_columns is None:
            raise ValueError("CICIoT2023 materialization requires configured model features")
        payload_file = staging_root / "materialized.parquet"
        normalization = normalize_materialized_parquet(
            unprocessed_payload,
            payload_file,
            feature_columns=feature_columns.order,
            strategy=materialization.normalization_strategy,
            scope=materialization.normalization_scope,
        )
        return MaterializationResult(
            staged_path=payload_file,
            row_count=report.written_rows,
            preprocessing_evidence=normalization.encode(),
        )
