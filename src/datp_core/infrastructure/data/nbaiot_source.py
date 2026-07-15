from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pa_csv
import pyarrow.parquet as pq
from blake3 import blake3

from datp_core.domain.data.datasets import SourceTrafficLabel
from datp_core.domain.errors import DatasetError
from datp_core.infrastructure.data.nbaiot_inspection import device_csv_files
from datp_core.infrastructure.data.streaming import update_row_order_checksum

_DEFAULT_CSV_BLOCK_BYTES = 8 * 1024 * 1024
_LABEL_COLUMN_NAME = "source_label"


@dataclass(frozen=True, slots=True, kw_only=True)
class NBaIoTDeviceMaterialization:
    device_id: str
    path: Path
    row_count: int
    row_order_checksum: str


@dataclass(frozen=True, slots=True, kw_only=True)
class NBaIoTChunkedSourceAdapter:
    raw_root: Path
    output_root: Path
    csv_block_bytes: int = _DEFAULT_CSV_BLOCK_BYTES

    def materialize_device(self, device_id: str) -> NBaIoTDeviceMaterialization:
        files = device_csv_files(self.raw_root / device_id)
        if not files:
            raise _dataset_error(f"no source files found for device {device_id!r}")
        destination = self.output_root / device_id / "source.parquet"
        destination.parent.mkdir(parents=True, exist_ok=True)
        hasher = blake3()
        row_count = 0
        expected_schema: pa.Schema | None = None
        writer: pq.ParquetWriter | None = None
        try:
            for csv_path, label in files:
                try:
                    reader = pa_csv.open_csv(csv_path, read_options=pa_csv.ReadOptions(block_size=self.csv_block_bytes))
                    for batch in reader:
                        labeled_batch = _with_label_column(batch, label)
                        if expected_schema is None:
                            expected_schema = labeled_batch.schema
                            writer = pq.ParquetWriter(destination, expected_schema)
                        elif labeled_batch.schema != expected_schema:
                            raise _dataset_error(f"{csv_path} changed schema mid-stream during materialization")
                        if writer is None:
                            raise _dataset_error(f"{csv_path} could not open a parquet writer")
                        writer.write_batch(labeled_batch)
                        update_row_order_checksum(hasher, labeled_batch)
                        row_count += labeled_batch.num_rows
                except pa.ArrowInvalid as error:
                    raise _dataset_error(
                        f"{csv_path} could not be parsed at the configured CSV block size "
                        f"({self.csv_block_bytes} bytes); it may be too small to hold one row"
                    ) from error
        finally:
            if writer is not None:
                writer.close()
        if expected_schema is None:
            raise _dataset_error(f"device {device_id!r} produced no rows to materialize")
        return NBaIoTDeviceMaterialization(
            device_id=device_id,
            path=destination,
            row_count=row_count,
            row_order_checksum=hasher.hexdigest(),
        )


def _with_label_column(batch: pa.RecordBatch, label: SourceTrafficLabel) -> pa.RecordBatch:
    label_array = pa.array([label.value] * batch.num_rows, type=pa.string())
    columns = [batch.column(index) for index in range(batch.num_columns)]
    names = [*batch.schema.names, _LABEL_COLUMN_NAME]
    return pa.RecordBatch.from_arrays([*columns, label_array], names)


def _dataset_error(coverage: str) -> DatasetError:
    return DatasetError(dataset="n_baiot", regime="unresolved", coverage=coverage, detail=coverage)
