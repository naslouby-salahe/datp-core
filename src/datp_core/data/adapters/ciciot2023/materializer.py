"""Canonical out-of-core CICIoT2023 materialization."""

from __future__ import annotations

from pathlib import Path
from random import Random

import duckdb
import pyarrow as pa

from datp_core.data.contracts.enums import (
    ArtifactSchemaVersion,
    AttackAssignment,
    CsvColumnKind,
    DataFailureCode,
    DeduplicationPolicy,
    MaterializedColumn,
    SplitMembership,
)
from datp_core.data.contracts.values import ColumnName
from datp_core.data.materialization.database import (
    fetch_scalar,
    insert_record_batch,
    quote_identifier,
    write_query_to_parquet,
)
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.materialization.models import (
    CICIoT2023MaterializationPlan,
    MaterializationEvidence,
)
from datp_core.data.materialization.semantics import (
    ciciot_equivalence_digest,
    normalize_label,
    split_membership_for_draw,
)
from datp_core.data.sources.csv import CsvBatchStream, CsvColumnSpec, CsvReadPlan
from datp_core.data.sources.models import SourceInventory


def materialize_ciciot2023(
    connection: duckdb.DuckDBPyConnection,
    plan: CICIoT2023MaterializationPlan,
    inventory: SourceInventory,
    target_path: Path,
) -> MaterializationEvidence:
    if plan.split.attack_assignment is not AttackAssignment.TEST:
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            "CICIoT2023 requires attack rows to be assigned to test",
            source_path=None,
            source_row_index=None,
        )
    if plan.split.deduplication is not DeduplicationPolicy.EXACT_WITHIN_CLASS:
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            "CICIoT2023 requires exact within-class deduplication",
            source_path=None,
            source_row_index=None,
        )
    feature_names = tuple(feature.value for feature in plan.source.feature_columns)
    _create_raw_table(connection, feature_names)
    seen = excluded = valid = 0
    benign_label = normalize_label(plan.source.benign_label.value, plan.source.label_case_policy)
    for entry in inventory.executable_entries:
        stream = CsvBatchStream(
            CsvReadPlan(
                source_path=entry.source_path,
                columns=tuple(
                    CsvColumnSpec(
                        name=ColumnName(feature.value),
                        kind=CsvColumnKind.FLOAT64,
                        nullable=False,
                        strip_text=False,
                    )
                    for feature in plan.source.feature_columns
                )
                + (
                    CsvColumnSpec(
                        name=plan.source.multiclass_label_column,
                        kind=CsvColumnKind.TEXT,
                        nullable=False,
                        strip_text=True,
                    ),
                ),
                invalid_row_policy=plan.source.invalid_row_policy,
                chunk_row_count=int(plan.runtime.chunk_row_count),
            )
        )
        for csv_batch in stream:
            expanded = _expand_batch(
                csv_batch.record_batch,
                entry.source_path,
                feature_names,
                benign_label,
                plan,
            )
            insert_record_batch(
                connection,
                "raw_rows",
                expanded,
                "SELECT * FROM __datp_batch",
                (),
            )
        report = stream.report
        seen += report.source_rows_seen
        excluded += report.excluded_rows
        valid += report.valid_rows
    if valid == 0:
        raise DataFailure(
            DataFailureCode.SOURCE_EMPTY,
            "CICIoT2023 contains no valid source rows",
            source_path=None,
            source_row_index=None,
        )
    _create_canonical_table(connection, feature_names)
    canonical_rows = fetch_scalar(connection, "SELECT count(*) FROM canonical_rows")
    conflicting_groups = _conflicting_group_count(connection, feature_names)
    _create_split_assignments(connection)
    _assign_benign_splits(connection, plan)
    query = _final_query(feature_names)
    written_rows = write_query_to_parquet(connection, query, target_path, plan.runtime)
    return MaterializationEvidence(
        schema_version=ArtifactSchemaVersion.MATERIALIZED_V1.value,
        source_rows_seen=seen,
        excluded_rows=excluded,
        canonical_rows=canonical_rows,
        duplicate_rows_removed=valid - canonical_rows,
        conflicting_label_feature_group_count=conflicting_groups,
        written_rows=written_rows,
        encoded_feature_names=feature_names,
    )


def _create_raw_table(connection: duckdb.DuckDBPyConnection, feature_names: tuple[str, ...]) -> None:
    features = ", ".join(f"{quote_identifier(name)} DOUBLE NOT NULL" for name in feature_names)
    connection.execute(
        "CREATE TABLE raw_rows ("
        f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} VARCHAR NOT NULL, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} BIGINT NOT NULL, "
        f"{quote_identifier(MaterializedColumn.CLIENT_ID.value)} VARCHAR NOT NULL, "
        f"{quote_identifier(MaterializedColumn.IS_ATTACK.value)} BOOLEAN NOT NULL, "
        f"{quote_identifier(MaterializedColumn.MULTICLASS_LABEL.value)} VARCHAR NOT NULL, "
        "class_digest BLOB NOT NULL, "
        f"{features})"
    )


def _expand_batch(
    batch: pa.RecordBatch,
    source_path: Path,
    feature_names: tuple[str, ...],
    benign_label: str,
    plan: CICIoT2023MaterializationPlan,
) -> pa.RecordBatch:
    source_paths: list[str] = []
    source_indices: list[int] = []
    client_ids: list[str] = []
    attacks: list[bool] = []
    labels: list[str] = []
    digests: list[bytes] = []
    feature_values = tuple(batch.column(index) for index in range(len(feature_names)))
    label_values = batch.column(len(feature_names))
    row_index_values = batch.column(len(feature_names) + 1)
    for row_index in range(batch.num_rows):
        numeric = tuple(float(column[row_index].as_py()) for column in feature_values)
        label = str(label_values[row_index].as_py()).strip()
        normalized = normalize_label(label, plan.source.label_case_policy)
        is_attack = normalized != benign_label
        source_paths.append(source_path.as_posix())
        source_indices.append(int(row_index_values[row_index].as_py()))
        client_ids.append(source_path.name)
        attacks.append(is_attack)
        labels.append(label)
        digests.append(ciciot_equivalence_digest(is_attack, numeric, plan.runtime.row_digest))
    arrays: list[pa.Array] = [
        pa.array(source_paths, type=pa.string()),
        pa.array(source_indices, type=pa.int64()),
        pa.array(client_ids, type=pa.string()),
        pa.array(attacks, type=pa.bool_()),
        pa.array(labels, type=pa.string()),
        pa.array(digests, type=pa.binary()),
    ]
    arrays.extend(feature_values)
    names = [
        MaterializedColumn.SOURCE_PATH.value,
        MaterializedColumn.SOURCE_ROW_INDEX.value,
        MaterializedColumn.CLIENT_ID.value,
        MaterializedColumn.IS_ATTACK.value,
        MaterializedColumn.MULTICLASS_LABEL.value,
        "class_digest",
        *feature_names,
    ]
    return pa.RecordBatch.from_arrays(arrays, names)


def _create_canonical_table(connection: duckdb.DuckDBPyConnection, feature_names: tuple[str, ...]) -> None:
    partition = ", ".join(
        (quote_identifier(MaterializedColumn.IS_ATTACK.value),)
        + tuple(quote_identifier(name) for name in feature_names)
    )
    connection.execute(
        "CREATE TABLE canonical_rows AS "
        "SELECT * EXCLUDE (__canonical_rank) FROM ("
        "SELECT *, row_number() OVER (PARTITION BY "
        f"{partition} ORDER BY {quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}) AS __canonical_rank "
        "FROM raw_rows) WHERE __canonical_rank = 1"
    )


def _conflicting_group_count(connection: duckdb.DuckDBPyConnection, feature_names: tuple[str, ...]) -> int:
    features = ", ".join(quote_identifier(name) for name in feature_names)
    return fetch_scalar(
        connection,
        "SELECT count(*) FROM ("
        f"SELECT {features} FROM canonical_rows GROUP BY {features} "
        f"HAVING count(DISTINCT {quote_identifier(MaterializedColumn.IS_ATTACK.value)}) > 1)",
    )


def _create_split_assignments(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        "CREATE TABLE split_assignments ("
        f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} VARCHAR NOT NULL, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} BIGINT NOT NULL, "
        f"{quote_identifier(MaterializedColumn.SPLIT.value)} VARCHAR NOT NULL, "
        f"PRIMARY KEY ({quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}))"
    )


def _assign_benign_splits(
    connection: duckdb.DuckDBPyConnection,
    plan: CICIoT2023MaterializationPlan,
) -> None:
    generator = Random(int(plan.split.seed.value))
    reader = connection.execute(
        "SELECT "
        f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} "
        "FROM canonical_rows "
        f"WHERE NOT {quote_identifier(MaterializedColumn.IS_ATTACK.value)} "
        "ORDER BY class_digest, "
        f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}"
    ).fetch_record_batch(rows_per_batch=int(plan.runtime.chunk_row_count))
    for batch in reader:
        roles = tuple(
            split_membership_for_draw(generator.random(), plan.split.ratios).value
            for _ in range(batch.num_rows)
        )
        assignment_batch = pa.RecordBatch.from_arrays(
            (batch.column(0), batch.column(1), pa.array(roles, type=pa.string())),
            (
                MaterializedColumn.SOURCE_PATH.value,
                MaterializedColumn.SOURCE_ROW_INDEX.value,
                MaterializedColumn.SPLIT.value,
            ),
        )
        insert_record_batch(
            connection,
            "split_assignments",
            assignment_batch,
            "SELECT * FROM __datp_batch",
            (),
        )


def _final_query(feature_names: tuple[str, ...]) -> str:
    feature_projection = ", ".join(f"c.{quote_identifier(name)}" for name in feature_names)
    split_column = quote_identifier(MaterializedColumn.SPLIT.value)
    role_expression = (
        f"CASE WHEN c.{quote_identifier(MaterializedColumn.IS_ATTACK.value)} "
        f"THEN {repr(SplitMembership.TEST.value)} ELSE a.{split_column} END"
    )
    return (
        "SELECT "
        f"{role_expression} AS {split_column}, "
        f"c.{quote_identifier(MaterializedColumn.CLIENT_ID.value)}, "
        f"c.{quote_identifier(MaterializedColumn.IS_ATTACK.value)}, "
        f"c.{quote_identifier(MaterializedColumn.MULTICLASS_LABEL.value)}, "
        f"c.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"c.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}, "
        f"{feature_projection} "
        "FROM canonical_rows c LEFT JOIN split_assignments a ON "
        f"c.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} = "
        f"a.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} AND "
        f"c.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} = "
        f"a.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} "
        f"ORDER BY CASE {role_expression} "
        f"WHEN {repr(SplitMembership.TRAIN.value)} THEN 0 "
        f"WHEN {repr(SplitMembership.CALIBRATION.value)} THEN 1 ELSE 2 END, "
        f"c.{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
        f"c.{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}"
    )
