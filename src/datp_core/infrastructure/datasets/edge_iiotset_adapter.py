"""Edge-IIoTset materialization bound to its folder-defined client and split contracts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from attrs import define

from datp_core.application.ports import MaterializationPayload, SourceInventory
from datp_core.domain.catalogue import SweepConditionRecord
from datp_core.domain.datasets import (
    AdapterKind,
    CategoricalEncodingRecord,
    DatasetMaterialization,
    DatasetSetup,
    PartitionSeedContract,
    ResolvedDataset,
)
from datp_core.infrastructure.datasets.csv_source import SourceRowFailure
from datp_core.infrastructure.datasets.edge_iiotset import (
    EdgeIIoTsetRow,
    EdgeTimestampedRow,
    encode_edge_chronological_split_as_parquet,
    encode_edge_split_as_parquet,
    fit_edge_train_normalization,
    fit_edge_vocabulary,
    iter_edge_iiotset_source,
    split_edge_benign_rows,
    split_edge_chronological_rows,
)


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetMaterializationPayload:
    staged_path: Path
    row_count: int
    preprocessing_evidence: bytes
    partition_evidence: bytes | None = None


class EdgeIIoTsetAdapter:
    """Materialize standard and temporal Edge populations without assigning attacks to clients."""

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
    ) -> MaterializationPayload:
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
        rows = _read_rows(
            inventory,
            normal_root,
            attack_root,
            numeric.order,
            categorical.columns,
            inspection.binary_label_header,
            labels.multiclass_label.column,
            timestamp_header if materialization.split_method == "within_client_chronological" else None,
            excluded,
        )
        rows = tuple(row for row in rows if row.client_id not in excluded)
        payload_file = staging_root / "materialized.parquet"
        if materialization.split_method == "random_fractional":
            split = split_edge_benign_rows(rows, materialization)
            vocabulary = fit_edge_vocabulary(split.train, categorical.columns)
            normalization = fit_edge_train_normalization(split.train)
            payload = encode_edge_split_as_parquet(split, numeric.order, vocabulary, normalization)
            evidence = {"split_method": materialization.split_method, "excluded_clients": sorted(excluded)}
        elif materialization.split_method == "within_client_chronological":
            chronological = split_edge_chronological_rows(
                tuple(
                    EdgeTimestampedRow(row=row, time_of_day_seconds=_require_timestamp(row))
                    for row in _deduplicated_benign_rows(rows)
                ),
                materialization,
                (),
            )
            _validate_chronological_minimums(chronological, materialization)
            vocabulary = fit_edge_vocabulary(chronological.historical_train, categorical.columns)
            normalization = fit_edge_train_normalization(chronological.historical_train)
            payload = encode_edge_chronological_split_as_parquet(
                chronological, numeric.order, vocabulary, normalization
            )
            evidence = {
                "split_method": materialization.split_method,
                "excluded_clients": sorted(excluded),
                "chronology_validation": "passed",
            }
        else:
            raise ValueError(f"Unsupported Edge-IIoTset split method '{materialization.split_method}'")
        payload_file.write_bytes(payload)
        return EdgeIIoTsetMaterializationPayload(
            staged_path=payload_file,
            row_count=len(rows),
            preprocessing_evidence=json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode(),
        )


def _read_rows(
    inventory: SourceInventory,
    normal_root: Path,
    attack_root: Path,
    numeric_headers: tuple[str, ...],
    categorical_headers: tuple[str, ...],
    binary_label_header: str,
    multiclass_label_header: str,
    timestamp_header: str | None,
    excluded_clients: frozenset[str],
) -> tuple[EdgeIIoTsetRow, ...]:
    rows: list[EdgeIIoTsetRow] = []
    failures: list[str] = []
    for entry in inventory.entries:
        try:
            client_id = entry.source_path.relative_to(normal_root).parts[0]
        except ValueError:
            client_id = None
        if client_id in excluded_clients:
            continue
        for result in iter_edge_iiotset_source(
            entry.source_path,
            normal_root,
            attack_root,
            numeric_headers,
            categorical_headers,
            binary_label_header,
            multiclass_label_header,
            timestamp_header,
        ):
            if isinstance(result, SourceRowFailure):
                failures.append(f"{result.source_path}:{result.source_row_index}: {result.reason}")
            else:
                rows.append(result)
    if not rows:
        raise ValueError("Edge-IIoTset materialization found no valid source rows")
    return tuple(rows)


def _require_timestamp(row: EdgeIIoTsetRow) -> float:
    if row.time_of_day_seconds is None:
        raise ValueError(f"Temporal Edge-IIoTset row lacks a timestamp: {row.source_path}:{row.source_row_index}")
    return row.time_of_day_seconds


def _deduplicated_benign_rows(rows: tuple[EdgeIIoTsetRow, ...]) -> tuple[EdgeIIoTsetRow, ...]:
    canonical: dict[tuple[str, tuple[float, ...], tuple[str | None, ...]], EdgeIIoTsetRow] = {}
    for row in sorted(rows, key=lambda value: (value.source_path.as_posix(), value.source_row_index)):
        if row.is_attack:
            continue
        if row.client_id is None:
            raise ValueError("Edge-IIoTset benign rows require a folder-defined client")
        canonical.setdefault((row.client_id, row.numeric_values, row.categorical_values), row)
    if not canonical:
        raise ValueError("Temporal Edge-IIoTset materialization found no benign rows")
    return tuple(canonical.values())


def _validate_chronological_minimums(split, materialization: DatasetMaterialization) -> None:
    minimums = materialization.split_minimum_row_counts or {}
    roles = {
        "historical_train": split.historical_train,
        "historical_calibration": split.historical_calibration,
        "future_recalibration": split.future_recalibration,
        "future_evaluation": split.future_evaluation,
    }
    for client_id in {row.client_id for rows in roles.values() for row in rows}:
        if client_id is None:
            raise ValueError("Chronological Edge-IIoTset split contains an unassigned client")
        for role, rows in roles.items():
            required = minimums.get(role, 1)
            if sum(row.client_id == client_id for row in rows) < required:
                raise ValueError(f"Temporal client '{client_id}' lacks the configured minimum for {role}")
