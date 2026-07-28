"""DuckDB and Parquet boundary helpers."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from datp_core.data.contracts.materialization import DataLoadingConfig
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.contracts.enums import DataFailureCode, ParquetCompression


def open_database(database_path: Path, temporary_directory: Path, runtime: DataLoadingConfig) -> duckdb.DuckDBPyConnection:
    temporary_directory.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(database_path.as_posix())
    connection.execute(f"SET threads = {int(runtime.duckdb.threads)}")
    connection.execute("SET memory_limit = " + quote_literal(runtime.duckdb.memory_limit))
    connection.execute("SET temp_directory = " + quote_literal(temporary_directory.as_posix()))
    connection.execute(
        "SET preserve_insertion_order = " + ("true" if runtime.duckdb.preserve_insertion_order else "false")
    )
    return connection


def insert_record_batch(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    batch: pa.RecordBatch,
    projection_sql: str,
    parameters: tuple[str | int | bool | None, ...],
) -> None:
    relation_name = "__datp_batch"
    connection.register(relation_name, batch)
    try:
        connection.execute(f"INSERT INTO {quote_identifier(table_name)} {projection_sql}", parameters)
    finally:
        connection.unregister(relation_name)


def write_query_to_parquet(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    target_path: Path,
    runtime: DataLoadingConfig,
) -> int:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    reader = connection.execute(query).fetch_record_batch(rows_per_batch=int(runtime.chunk_row_count))
    compression = None if runtime.parquet.compression is ParquetCompression.NONE else runtime.parquet.compression.value
    written_rows = 0
    with pq.ParquetWriter(
        target_path,
        reader.schema,
        compression=compression,
        use_dictionary=runtime.parquet.dictionary_encoding,
        data_page_size=int(runtime.parquet.data_page_size),
    ) as writer:
        for batch in reader:
            writer.write_batch(batch, row_group_size=int(runtime.parquet.row_group_size))
            written_rows += batch.num_rows
    return written_rows


def iter_query_batches(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    chunk_row_count: int,
) -> Iterator[pa.RecordBatch]:
    reader = connection.execute(query).fetch_record_batch(rows_per_batch=chunk_row_count)
    yield from reader


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def require_non_empty_parquet(path: Path) -> None:
    if not path.is_file():
        raise DataFailure(
            DataFailureCode.ARTIFACT,
            "expected Parquet artifact was not created",
            source_path=path,
            source_row_index=None,
        )
    metadata = pq.ParquetFile(path).metadata
    if metadata is None or metadata.num_rows == 0:
        raise DataFailure(
            DataFailureCode.SOURCE_EMPTY,
            "materialized Parquet artifact contains no rows",
            source_path=path,
            source_row_index=None,
        )
