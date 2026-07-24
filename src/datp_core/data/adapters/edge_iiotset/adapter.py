"""Edge-IIoTset adapter entry point — orchestration only."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from datp_core.data.adapters.edge_iiotset.models import EdgeTimestampedRow
from datp_core.data.adapters.edge_iiotset.parquet import (
    _deduplicated_edge_benign_rows,
    _read_edge_rows,
    _require_edge_timestamp,
    _validate_edge_chronological_minimums,
    encode_edge_chronological_split_as_parquet,
    encode_edge_split_as_parquet,
)
from datp_core.data.adapters.edge_iiotset.preprocessing import fit_edge_train_normalization, fit_edge_vocabulary
from datp_core.data.adapters.edge_iiotset.splitting import (
    split_edge_benign_rows,
    split_edge_chronological_rows,
)
from datp_core.data.contracts.dataset import DatasetSetup, ResolvedDataset
from datp_core.data.contracts.enums import AdapterKind, SplitMethod
from datp_core.data.contracts.features import CategoricalEncodingRecord
from datp_core.data.contracts.materialization import DatasetMaterialization, PartitionSeedContract
from datp_core.data.materialization.models import MaterializationResult
from datp_core.data.materialization.ports import SourceInventory
from datp_core.experiments import SweepConditionRecord


class EdgeIIoTsetAdapter:
    @property
    def adapter_kind(self) -> AdapterKind:
        return AdapterKind.EDGE_IIOTSET

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
            raise ValueError("Edge-IIoTset does not support partition-condition materialization")
        numeric = dataset.field_schema.retained_numeric_features
        categorical = dataset.field_schema.categorical_encoding
        labels = dataset.field_schema.label_fields
        inspection = dataset.inspection_contract
        if (
            numeric is None
            or not isinstance(categorical, CategoricalEncodingRecord)
            or labels.multiclass_label is None
            or inspection.normal_traffic_root is None
            or inspection.attack_traffic_root is None
            or inspection.binary_label_header is None
        ):
            raise ValueError("Edge-IIoTset materialization requires its resolved feature, label, and source contracts")
        timestamp = dataset.field_schema.identity_scheme.timestamp_field
        timestamp_header = timestamp.get("column") if isinstance(timestamp, Mapping) else timestamp
        if not isinstance(timestamp_header, str):
            raise ValueError("Edge-IIoTset timestamp field must resolve to a column name")
        normal_root = (dataset.paths.raw_data_root / inspection.normal_traffic_root.value).resolve()
        attack_root = (dataset.paths.raw_data_root / inspection.attack_traffic_root.value).resolve()
        excluded = frozenset(materialization.split_excluded_client_folders or ())
        rows = _read_edge_rows(
            inventory,
            normal_root,
            attack_root,
            numeric.order,
            categorical.columns,
            inspection.binary_label_header,
            labels.multiclass_label.column,
            timestamp_header if materialization.split_method == SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL else None,
            excluded,
        )
        rows = tuple(row for row in rows if row.client_id not in excluded)
        payload_file = staging_root / "materialized.parquet"
        if materialization.split_method == SplitMethod.RANDOM_FRACTIONAL:
            split = split_edge_benign_rows(rows, materialization)
            vocabulary = fit_edge_vocabulary(split.train, categorical.columns)
            normalization = fit_edge_train_normalization(split.train)
            payload = encode_edge_split_as_parquet(split, numeric.order, vocabulary, normalization)
            evidence = {"split_method": materialization.split_method.value, "excluded_clients": sorted(excluded)}
        elif materialization.split_method == SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL:
            chronological = split_edge_chronological_rows(
                tuple(
                    EdgeTimestampedRow(row=row, time_of_day_seconds=_require_edge_timestamp(row))
                    for row in _deduplicated_edge_benign_rows(rows)
                ),
                materialization,
                (),
            )
            _validate_edge_chronological_minimums(chronological, materialization)
            vocabulary = fit_edge_vocabulary(chronological.historical_train, categorical.columns)
            normalization = fit_edge_train_normalization(chronological.historical_train)
            payload = encode_edge_chronological_split_as_parquet(
                chronological, numeric.order, vocabulary, normalization
            )
            evidence = {
                "split_method": materialization.split_method.value,
                "excluded_clients": sorted(excluded),
                "chronology_validation": "passed",
            }
        else:
            raise ValueError(f"Unsupported Edge-IIoTset split method '{materialization.split_method}'")
        payload_file.write_bytes(payload)
        return MaterializationResult(
            staged_path=payload_file,
            row_count=len(rows),
            preprocessing_evidence=json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode(),
        )
