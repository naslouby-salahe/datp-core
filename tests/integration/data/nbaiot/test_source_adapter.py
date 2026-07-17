from pathlib import Path

import pyarrow.parquet as pq
import pytest

from datp_core.domain.errors import DatasetError
from datp_core.infrastructure.data.nbaiot.source import NBaIoTChunkedSourceAdapter

_FEATURE_COLUMNS = "feature_a,feature_b,feature_c"


def _write_csv(path: Path, *, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [_FEATURE_COLUMNS]
    lines.extend(f"{index}.0,{index * 2}.0,{index * 3}.0" for index in range(rows))
    path.write_text("\n".join(lines) + "\n")


def _write_synthetic_device(raw_root: Path, *, device_id: str, rows_per_file: int) -> None:
    _write_csv(raw_root / device_id / "benign_traffic.csv", rows=rows_per_file)
    _write_csv(raw_root / device_id / "gafgyt_attacks" / "combo.csv", rows=rows_per_file)
    _write_csv(raw_root / device_id / "gafgyt_attacks" / "udp.csv", rows=rows_per_file)
    _write_csv(raw_root / device_id / "mirai_attacks" / "syn.csv", rows=rows_per_file)


def test_materialization_is_bounded_and_labels_every_row(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _write_synthetic_device(raw_root, device_id="DeviceOne", rows_per_file=6)
    adapter = NBaIoTChunkedSourceAdapter(raw_root=raw_root, output_root=tmp_path / "processed", csv_block_bytes=64)

    result = adapter.materialize_device("DeviceOne")

    assert result.row_count == 24
    table = pq.read_table(result.path)
    assert table.num_rows == 24
    assert "source_label" in table.schema.names
    labels = table.column(table.schema.get_field_index("source_label")).to_pylist()
    assert labels.count("benign") == 6
    assert labels.count("gafgyt") == 12
    assert labels.count("mirai") == 6


def test_materialization_checksum_is_identical_across_different_csv_block_sizes(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _write_synthetic_device(raw_root, device_id="DeviceOne", rows_per_file=9)

    small_blocks = NBaIoTChunkedSourceAdapter(
        raw_root=raw_root, output_root=tmp_path / "small", csv_block_bytes=32
    ).materialize_device("DeviceOne")
    large_blocks = NBaIoTChunkedSourceAdapter(
        raw_root=raw_root, output_root=tmp_path / "large", csv_block_bytes=1024 * 1024
    ).materialize_device("DeviceOne")

    assert small_blocks.row_count == large_blocks.row_count
    assert small_blocks.row_order_checksum == large_blocks.row_order_checksum


def test_materialization_rejects_a_device_with_no_source_files(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    (raw_root / "DeviceEmpty").mkdir(parents=True)
    adapter = NBaIoTChunkedSourceAdapter(
        raw_root=raw_root, output_root=tmp_path / "processed", csv_block_bytes=8 * 1024 * 1024
    )

    with pytest.raises(DatasetError):
        adapter.materialize_device("DeviceEmpty")
