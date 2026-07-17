from dataclasses import dataclass, field
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pa_csv
import pyarrow.parquet as pq
from blake3 import blake3

from datp_core.domain.data.datasets import SourceTrafficLabel
from datp_core.domain.errors import DatasetError
from datp_core.infrastructure.data.nbaiot_inspection import device_csv_files
from datp_core.infrastructure.data.streaming import update_row_order_checksum

SOURCE_LABEL_COLUMN_NAME = "source_label"


@dataclass(frozen=True, slots=True, kw_only=True)
class NBaIoTDeviceMaterialization:
    device_id: str
    path: Path
    row_count: int
    row_order_checksum: str


@dataclass(slots=True)
class _MaterializationState:
    destination: Path
    hasher: blake3 = field(default_factory=blake3)
    row_count: int = 0
    expected_schema: pa.Schema | None = None
    writer: pq.ParquetWriter | None = None


def _write_labeled_batch(*, state: _MaterializationState, labeled_batch: pa.RecordBatch, csv_path: Path) -> None:
    if state.expected_schema is None:
        state.expected_schema = labeled_batch.schema
        state.writer = pq.ParquetWriter(state.destination, state.expected_schema)
    elif labeled_batch.schema != state.expected_schema:
        raise _dataset_error(f"{csv_path} changed schema mid-stream during materialization")
    if state.writer is None:
        raise _dataset_error(f"{csv_path} could not open a parquet writer")
    state.writer.write_batch(labeled_batch)
    update_row_order_checksum(state.hasher, labeled_batch)
    state.row_count += labeled_batch.num_rows


def _materialize_one_file(
    *, csv_path: Path, label: SourceTrafficLabel, csv_block_bytes: int, state: _MaterializationState
) -> None:
    try:
        reader = pa_csv.open_csv(csv_path, read_options=pa_csv.ReadOptions(block_size=csv_block_bytes))
        for batch in reader:
            _write_labeled_batch(state=state, labeled_batch=_with_label_column(batch, label), csv_path=csv_path)
    except pa.ArrowInvalid as error:
        raise _dataset_error(
            f"{csv_path} could not be parsed at the configured CSV block size "
            f"({csv_block_bytes} bytes); it may be too small to hold one row"
        ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class NBaIoTChunkedSourceAdapter:
    raw_root: Path
    output_root: Path
    csv_block_bytes: int

    def materialize_device(self, device_id: str) -> NBaIoTDeviceMaterialization:
        files = device_csv_files(self.raw_root / device_id)
        if not files:
            raise _dataset_error(f"no source files found for device {device_id!r}")
        destination = self.output_root / device_id / "source.parquet"
        destination.parent.mkdir(parents=True, exist_ok=True)
        state = _MaterializationState(destination=destination)
        try:
            for csv_path, label in files:
                _materialize_one_file(csv_path=csv_path, label=label, csv_block_bytes=self.csv_block_bytes, state=state)
        finally:
            if state.writer is not None:
                state.writer.close()
        if state.expected_schema is None:
            raise _dataset_error(f"device {device_id!r} produced no rows to materialize")
        return NBaIoTDeviceMaterialization(
            device_id=device_id,
            path=destination,
            row_count=state.row_count,
            row_order_checksum=state.hasher.hexdigest(),
        )


def _with_label_column(batch: pa.RecordBatch, label: SourceTrafficLabel) -> pa.RecordBatch:
    label_array = pa.array([label.value] * batch.num_rows, type=pa.string())
    columns = [batch.column(index) for index in range(batch.num_columns)]
    names = [*batch.schema.names, SOURCE_LABEL_COLUMN_NAME]
    return pa.RecordBatch.from_arrays([*columns, label_array], names)


def _dataset_error(coverage: str) -> DatasetError:
    return DatasetError(dataset="n_baiot", regime="unresolved", coverage=coverage, detail=coverage)
