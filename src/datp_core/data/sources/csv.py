"""Bounded-memory CSV parsing into Arrow record batches."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterator
from pathlib import Path

import msgspec
import pyarrow as pa

from datp_core.data.contracts.enums import CsvColumnKind, DataFailureCode, InvalidRowPolicy
from datp_core.data.contracts.values import ColumnName
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.sources.models import CsvBatch, MutableCsvReadState


class CsvColumnSpec(msgspec.Struct, frozen=True):
    name: ColumnName
    kind: CsvColumnKind
    nullable: bool
    strip_text: bool


class CsvReadPlan(msgspec.Struct, frozen=True):
    source_path: Path
    columns: tuple[CsvColumnSpec, ...]
    invalid_row_policy: InvalidRowPolicy
    chunk_row_count: int


class CsvBatchStream:
    __slots__ = ("_plan", "_state")

    def __init__(self, plan: CsvReadPlan) -> None:
        if plan.chunk_row_count <= 0:
            raise DataFailure(
                DataFailureCode.CONFIGURATION,
                "CSV chunk row count must be positive",
                source_path=plan.source_path,
                source_row_index=None,
            )
        self._plan = plan
        self._state = MutableCsvReadState()

    @property
    def report(self):
        return self._state.freeze()

    def __iter__(self) -> Iterator[CsvBatch]:
        with self._plan.source_path.open("r", encoding="utf-8", newline="") as source:
            reader = csv.reader(source)
            try:
                header = tuple(next(reader))
            except StopIteration as exc:
                raise DataFailure(
                    DataFailureCode.SOURCE_EMPTY,
                    "CSV source has no header",
                    source_path=self._plan.source_path,
                    source_row_index=None,
                ) from exc
            indices = self._resolve_indices(header)
            buffers = tuple([] for _ in self._plan.columns)
            row_indices: list[int] = []
            for source_row_index, row in enumerate(reader, start=1):
                self._state.source_rows_seen += 1
                parsed = self._parse_row(row, indices, source_row_index)
                if parsed is None:
                    continue
                for buffer, value in zip(buffers, parsed, strict=True):
                    buffer.append(value)
                row_indices.append(source_row_index)
                self._state.valid_rows += 1
                if len(row_indices) == self._plan.chunk_row_count:
                    yield CsvBatch(self._record_batch(buffers, row_indices))
                    self._clear(buffers, row_indices)
            if row_indices:
                yield CsvBatch(self._record_batch(buffers, row_indices))

    def _resolve_indices(self, header: tuple[str, ...]) -> tuple[int, ...]:
        missing = tuple(spec.name.value for spec in self._plan.columns if spec.name.value not in header)
        if missing:
            raise DataFailure(
                DataFailureCode.SOURCE_HEADER,
                "missing required CSV headers: " + ", ".join(missing),
                source_path=self._plan.source_path,
                source_row_index=None,
            )
        return tuple(header.index(spec.name.value) for spec in self._plan.columns)

    def _parse_row(
        self,
        row: list[str],
        indices: tuple[int, ...],
        source_row_index: int,
    ) -> tuple[float | str | None, ...] | None:
        if any(index >= len(row) for index in indices):
            return self._invalid("row has fewer fields than required", source_row_index)
        values: list[float | str | None] = []
        for spec, index in zip(self._plan.columns, indices, strict=True):
            raw = row[index]
            if spec.kind is CsvColumnKind.FLOAT64:
                try:
                    numeric = float(raw)
                except ValueError:
                    return self._invalid(f"column '{spec.name.value}' is not numeric", source_row_index)
                if not math.isfinite(numeric):
                    return self._invalid(f"column '{spec.name.value}' is not finite", source_row_index)
                values.append(numeric)
                continue
            text = raw.strip() if spec.strip_text else raw
            if not text:
                if spec.nullable:
                    values.append(None)
                    continue
                return self._invalid(f"column '{spec.name.value}' is blank", source_row_index)
            values.append(text)
        return tuple(values)

    def _invalid(self, detail: str, source_row_index: int) -> None:
        if self._plan.invalid_row_policy is InvalidRowPolicy.FAIL_SOURCE:
            raise DataFailure(
                DataFailureCode.SOURCE_ROW,
                detail,
                source_path=self._plan.source_path,
                source_row_index=source_row_index,
            )
        self._state.excluded_rows += 1
        return None

    def _record_batch(self, buffers: tuple[list[float | str | None], ...], row_indices: list[int]) -> pa.RecordBatch:
        arrays: list[pa.Array] = []
        names: list[str] = []
        for spec, buffer in zip(self._plan.columns, buffers, strict=True):
            arrow_type = pa.float64() if spec.kind is CsvColumnKind.FLOAT64 else pa.string()
            arrays.append(pa.array(buffer, type=arrow_type))
            names.append(spec.name.value)
        arrays.append(pa.array(row_indices, type=pa.int64()))
        names.append("source_row_index")
        return pa.RecordBatch.from_arrays(arrays, names)

    @staticmethod
    def _clear(buffers: tuple[list[float | str | None], ...], row_indices: list[int]) -> None:
        for buffer in buffers:
            buffer.clear()
        row_indices.clear()
