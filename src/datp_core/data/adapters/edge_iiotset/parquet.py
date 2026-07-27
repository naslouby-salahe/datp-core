"""Edge-IIoTset Parquet encoding."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import polars as pl

from datp_core.data.adapters.edge_iiotset.models import (
    EdgeChronologicalSplitRows,
    EdgeIIoTsetNormalization,
    EdgeIIoTsetRow,
    EdgeIIoTsetSplitRows,
    EdgeIIoTsetVocabulary,
)
from datp_core.data.contracts.materialization import DatasetMaterialization
from datp_core.data.materialization.ports import SourceInventory
from datp_core.data.sources.models import SourceRowFailure


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

    records: list[dict[str, object]] = []
    chronology_key = 0
    for role, rows in roles:
        for row in rows:
            if row.is_attack or row.client_id is None:
                raise ValueError("Edge-IIoTset client artifact may only contain benign assigned rows")
            record: dict[str, object] = {
                "split": role,
                "client_id": row.client_id,
                "source_path": row.source_path.as_posix(),
                "source_row_index": row.source_row_index,
                "is_attack": False,
            }
            if chronological:
                record["chronology_key"] = chronology_key
                chronology_key += 1
            for i, header in enumerate(numeric_headers):
                record[header] = float(row.numeric_values[i])
            for i, header in enumerate(categorical_headers):
                record[header] = row.categorical_values[i]
            records.append(record)

    df = pl.DataFrame(records)

    num_norm_exprs: list[pl.Expr] = []
    for i, header in enumerate(numeric_headers):
        low, high = normalization.minimums[i], normalization.maximums[i]
        if high == low:
            num_norm_exprs.append(pl.lit(0.0).alias(header))
        else:
            num_norm_exprs.append(((pl.col(header) - low) / (high - low)).alias(header))
    df = df.with_columns(num_norm_exprs)

    for header in categorical_headers:
        known = category_columns[header]
        fallback_categories = ("__MISSING__", "__UNKNOWN__")
        for category in (*known, *fallback_categories):
            col_name = f"{header}={category}"
            df = df.with_columns(pl.when(pl.col(header) == category).then(1.0).otherwise(0.0).alias(col_name))
        df = df.drop(header)

    base_cols = ["split", "client_id", "source_path", "source_row_index", "is_attack"]
    if chronological:
        base_cols.append("chronology_key")
    df = df.select(*base_cols, *encoded_headers)

    payload = BytesIO()
    df.write_parquet(payload, compression="zstd")
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
    split: EdgeChronologicalSplitRows, materialization: DatasetMaterialization
) -> None:
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
