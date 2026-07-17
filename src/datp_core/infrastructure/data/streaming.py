from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.dataset as ds
from blake3 import blake3
from msgspec import json

from datp_core.domain.runtime.admissibility import ChunkRowCount


@dataclass(frozen=True, slots=True, kw_only=True)
class ParquetBatchStream:
    path: Path
    batch_rows: ChunkRowCount

    def batches(self) -> Iterator[pa.RecordBatch]:
        dataset = self._dataset()
        scanner = dataset.scanner(batch_size=self.batch_rows.value, use_threads=False)
        reader = scanner.to_reader()
        yield from reader

    def schema(self) -> pa.Schema:
        return self._dataset().schema

    def row_order_checksum(self) -> str:
        hasher = blake3()
        for batch in self.batches():
            update_row_order_checksum(hasher, batch)
        return hasher.hexdigest()

    def bounded_pandas_chunks(self) -> Iterator["BoundedPandasChunk"]:
        for batch in self.batches():
            yield BoundedPandasChunk(frame=batch.to_pandas(), row_count=batch.num_rows)

    def _dataset(self) -> ds.Dataset:
        return ds.dataset(self.path, format="parquet")


@dataclass(frozen=True, slots=True, kw_only=True)
class BoundedPandasChunk:
    frame: object
    row_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class StreamingColumnStatistics:
    row_count: int
    minimum: float | None
    maximum: float | None
    mean: float | None
    variance: float | None


@dataclass(frozen=True, slots=True, kw_only=True)
class StreamingNumericProfile:
    statistics: tuple[StreamingColumnStatistics, ...]
    row_order_checksum: str


def numeric_column_statistics(stream: ParquetBatchStream, column: str) -> StreamingColumnStatistics:
    return numeric_column_profile(stream, (column,)).statistics[0]


def numeric_column_profile(stream: ParquetBatchStream, columns: tuple[str, ...]) -> StreamingNumericProfile:
    if not columns:
        return StreamingNumericProfile(statistics=(), row_order_checksum=stream.row_order_checksum())
    accumulators = [_NumericAccumulator() for _ in columns]
    hasher = blake3()
    for batch in stream.batches():
        _accumulate_numeric_batch(batch, columns, accumulators)
        update_row_order_checksum(hasher, batch)
    return StreamingNumericProfile(
        statistics=tuple(accumulator.statistics() for accumulator in accumulators),
        row_order_checksum=hasher.hexdigest(),
    )


def _accumulate_numeric_batch(
    batch: pa.RecordBatch,
    columns: tuple[str, ...],
    accumulators: list["_NumericAccumulator"],
) -> None:
    indexes = _numeric_column_indexes(batch.schema, columns)
    for accumulator, index in zip(accumulators, indexes, strict=True):
        accumulator.add(batch.column(index).to_pylist())


def _numeric_column_indexes(schema: pa.Schema, columns: tuple[str, ...]) -> tuple[int, ...]:
    indexes = tuple(schema.get_field_index(column) for column in columns)
    missing = tuple(column for column, index in zip(columns, indexes, strict=True) if index < 0)
    if missing:
        raise ValueError(f"source is missing numeric columns: {missing!r}")
    return indexes


def update_row_order_checksum(hasher: blake3, batch: pa.RecordBatch) -> None:
    columns = tuple(batch.column(index).to_pylist() for index in range(len(batch.schema.names)))
    for row_index in range(batch.num_rows):
        hasher.update(b"\\x1e")
        for column in columns:
            _update_length_delimited(hasher, json.encode(column[row_index]))


def _update_length_delimited(hasher: blake3, value: bytes) -> None:
    hasher.update(len(value).to_bytes(8, byteorder="big"))
    hasher.update(value)


@dataclass(slots=True)
class _NumericAccumulator:
    row_count: int = 0
    minimum: float | None = None
    maximum: float | None = None
    mean: float = 0.0
    sum_of_squared_deviations: float = 0.0

    def add(self, values: list[float | int | str | bool | Decimal | None]) -> None:
        numeric_values = tuple(float(value) for value in values if value is not None)
        if not numeric_values:
            return
        batch_minimum = min(numeric_values)
        batch_maximum = max(numeric_values)
        self.minimum = batch_minimum if self.minimum is None else min(self.minimum, batch_minimum)
        self.maximum = batch_maximum if self.maximum is None else max(self.maximum, batch_maximum)
        for value in numeric_values:
            self.row_count += 1
            delta = value - self.mean
            self.mean += delta / self.row_count
            self.sum_of_squared_deviations += delta * (value - self.mean)

    def statistics(self) -> StreamingColumnStatistics:
        if self.row_count == 0:
            return StreamingColumnStatistics(row_count=0, minimum=None, maximum=None, mean=None, variance=None)
        return StreamingColumnStatistics(
            row_count=self.row_count,
            minimum=self.minimum,
            maximum=self.maximum,
            mean=self.mean,
            variance=max(0.0, self.sum_of_squared_deviations / self.row_count),
        )
