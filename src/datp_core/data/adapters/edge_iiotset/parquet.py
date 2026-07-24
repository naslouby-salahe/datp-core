"""Edge-IIoTset Parquet encoding."""

from __future__ import annotations

import json
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from datp_core.data.adapters.edge_iiotset.models import (
    EdgeChronologicalSplitRows,
    EdgeIIoTsetNormalization,
    EdgeIIoTsetRow,
    EdgeIIoTsetSplitRows,
    EdgeIIoTsetVocabulary,
    EdgeTimestampedRow,
)
from datp_core.data.adapters.edge_iiotset.splitting import _provenance_key
from datp_core.data.contracts.features import CategoricalEncodingRecord
from datp_core.data.contracts.enums import SplitMethod
from datp_core.data.materialization.ports import SourceInventory
from datp_core.data.sources.models import SourceRowFailure


def _category_value(value: str | None, known: tuple[str, ...]) -> str:
    if value is None:
        return "__MISSING__"
    if value in known:
        return value
    return "__UNKNOWN__"


def _encode_edge_roles_as_parquet(
    roles: tuple[tuple[str, tuple[EdgeIIoTsetRow, ...]], ...],
    numeric_headers: tuple[str, ...],
    vocabulary: EdgeIIoTsetVocabulary,
    normalization: EdgeIIoTsetNormalization,
    *,
    chronological: bool,
) -> bytes:
    category_columns = dict(vocabulary.categories_by_column)
    categorical_headers = tuple(category_columns)
    if len(normalization.minimums) != len(numeric_headers) or len(normalization.maximums) != len(numeric_headers):
        raise ValueError("Edge-IIoTset normalization width differs from numeric schema")
    encoded_headers = list(numeric_headers)
    for header in categorical_headers:
        encoded_headers += [f"{header}={value}" for value in (*category_columns[header], "__MISSING__", "__UNKNOWN__")]
    records: dict[str, list[object]] = {
        "split": [],
        "client_id": [],
        "source_path": [],
        "source_row_index": [],
        "is_attack": [],
    }
    if chronological:
        records["chronology_key"] = []
    records.update({header: [] for header in encoded_headers})
    chronology_key = 0
    for role, rows in roles:
        for row in rows:
            if row.is_attack or row.client_id is None:
                raise ValueError("Edge-IIoTset client artifact may only contain benign assigned rows")
            records["split"].append(role)
            records["client_id"].append(row.client_id)
            records["source_path"].append(row.source_path.as_posix())
            records["source_row_index"].append(row.source_row_index)
            records["is_attack"].append(False)
            if chronological:
                records["chronology_key"].append(chronology_key)
                chronology_key += 1
            for i, header in enumerate(numeric_headers):
                low, high = normalization.minimums[i], normalization.maximums[i]
                records[header].append(0.0 if high == low else (row.numeric_values[i] - low) / (high - low))
            for i, header in enumerate(categorical_headers):
                value = row.categorical_values[i]
                selected = _category_value(value, category_columns[header])
                for category in (*category_columns[header], "__MISSING__", "__UNKNOWN__"):
                    records[f"{header}={category}"].append(float(category == selected))
    payload = BytesIO()
    pq.write_table(pa.table(records), payload, compression="zstd", use_dictionary=False)
    return payload.getvalue()


def encode_edge_split_as_parquet(
    split: EdgeIIoTsetSplitRows,
    numeric_headers: tuple[str, ...],
    vocabulary: EdgeIIoTsetVocabulary,
    normalization: EdgeIIoTsetNormalization,
) -> bytes:
    roles = (
        (("train", split.train), ("calibration", split.calibration))
        + (("recalibration_reference", split.recalibration_reference),)
        if split.recalibration_reference
        else (("train", split.train), ("calibration", split.calibration))
    ) + (("test", split.test),)
    return _encode_edge_roles_as_parquet(roles, numeric_headers, vocabulary, normalization, chronological=False)


def encode_edge_chronological_split_as_parquet(
    split: EdgeChronologicalSplitRows,
    numeric_headers: tuple[str, ...],
    vocabulary: EdgeIIoTsetVocabulary,
    normalization: EdgeIIoTsetNormalization,
) -> bytes:
    return _encode_edge_roles_as_parquet(
        (
            ("historical_training", split.historical_train),
            ("historical_calibration", split.historical_calibration),
            ("future_recalibration", split.future_recalibration),
            ("future_evaluation", split.future_evaluation),
        ),
        numeric_headers,
        vocabulary,
        normalization,
        chronological=True,
    )


def _read_edge_rows(
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
    from datp_core.data.adapters.edge_iiotset.parsing import iter_edge_iiotset_source

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


def _require_edge_timestamp(row: EdgeIIoTsetRow) -> float:
    if row.time_of_day_seconds is None:
        raise ValueError(f"Temporal Edge-IIoTset row lacks a timestamp: {row.source_path}:{row.source_row_index}")
    return row.time_of_day_seconds


def _deduplicated_edge_benign_rows(rows: tuple[EdgeIIoTsetRow, ...]) -> tuple[EdgeIIoTsetRow, ...]:
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


def _validate_edge_chronological_minimums(
    split: EdgeChronologicalSplitRows, materialization: "DatasetMaterialization"
) -> None:
    from datp_core.data.contracts.materialization import DatasetMaterialization

    minimums = materialization.split_minimum_row_counts or {}
    roles = {
        "historical_train": split.historical_train,
        "historical_calibration": split.historical_calibration,
        "future_recalibration": split.future_recalibration,
        "future_evaluation": split.future_evaluation,
    }
    missing_roles = sorted(set(roles) - set(minimums))
    if missing_roles:
        raise ValueError(
            f"Chronological Edge-IIoTset split is missing configured minimums for: {', '.join(missing_roles)}"
        )
    for client_id in {row.client_id for rows in roles.values() for row in rows}:
        if client_id is None:
            raise ValueError("Chronological Edge-IIoTset split contains an unassigned client")
        for role, rows in roles.items():
            required = minimums[role]
            if sum(row.client_id == client_id for row in rows) < required:
                raise ValueError(f"Temporal client '{client_id}' lacks the configured minimum for {role}")
